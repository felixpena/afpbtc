"""Pruebas sin internet: simulan la API de Bitview con datos sintéticos.

Ejecutar:  python -m unittest discover -s tests -v
"""

import json
import math
import os
import shutil
import tempfile
import unittest

from collector import collect, config, derive

N_DAYS = 6507  # 2009-01-01 .. 2026-10-25


def synthetic(series_name, n=N_DAYS):
    """Datos con forma realista: nulos al inicio y ciclos suaves."""
    out = []
    for i in range(n):
        if i < 600:
            out.append(None)
            continue
        t = i / 365
        price = 10 * math.exp(t * 0.55) * (1 + 0.5 * math.sin(t * 1.6))
        base = {
            "price": price,
            "market_cap": price * 19e6,
            "realized_cap": price * 19e6 / (1.6 + 0.9 * math.sin(t * 1.6)),
            "nupl": 0.3 + 0.3 * math.sin(t * 1.6),
            "lth_mvrv": 2 + math.sin(t * 1.6),
            "price_sma_200d": price * 0.95,
            "supply": 19e6,
            "lth_supply": 14e6,
            "hash_rate_sma_1w": 8e20,
        }.get(series_name, 1.0 + 0.1 * math.sin(i))
        out.append(base)
    return out


class FakeClient:
    base_url = "https://fake.bitview"

    def __init__(self, n=N_DAYS):
        self.n = n
        self.requests_made = 0
        self.calls = []

    def series_range(self, series, index="day1", start=0, end=None):
        self.requests_made += 1
        self.calls.append(("range", series))
        return {"start": 0, "data": synthetic(series, self.n)}

    def bulk(self, series_list, index="day1", start=-30):
        self.requests_made += 1
        self.calls.append(("bulk", tuple(series_list)))
        s = self.n + start
        return [{"start": s, "data": synthetic(name, self.n)[s:]} for name in series_list]

    def fees_recommended(self):
        return {"fastestFee": 2.5, "halfHourFee": 1.3, "hourFee": 0.6,
                "economyFee": 0.2, "minimumFee": 0.1}

    def tip_height(self):
        return 973093


class DeriveTests(unittest.TestCase):
    def test_ratio_handles_nulls_and_zero(self):
        self.assertEqual(derive.ratio([1, None, 4], [2, 3, 0]), [0.5, None, None])

    def test_zscore_needs_history(self):
        z = derive.mvrv_zscore([1.0] * 10, [0.5] * 10, min_points=365)
        self.assertTrue(all(v is None for v in z))

    def test_zscore_sign(self):
        mc = [100 + (i % 7) for i in range(400)]
        rc = [50] * 400
        z = derive.mvrv_zscore(mc, rc, min_points=365)
        self.assertGreater(z[-1], 0)

    def test_percentile_no_lookahead(self):
        vals = list(range(1000))
        p = derive.expanding_percentile(vals, 0, min_points=10)
        # Una serie siempre creciente queda en el percentil máximo cada día.
        self.assertGreater(p[500], 0.99)

    def test_phase(self):
        self.assertEqual(derive.phase(10), "Capitulación")
        self.assertEqual(derive.phase(46), "Optimismo")
        self.assertEqual(derive.phase(95), "Euforia")
        self.assertIsNone(derive.phase(None))

    def test_change(self):
        self.assertAlmostEqual(derive.change([100, None, 110], 2), 10.0)


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_full_then_incremental(self):
        c1 = FakeClient()
        collect.run(self.tmp, client=c1)
        self.assertEqual(sum(1 for k, _ in c1.calls if k == "range"), len(config.RAW_SERIES))

        with open(os.path.join(self.tmp, "latest.json"), encoding="utf-8") as fh:
            latest = json.load(fh)
        self.assertEqual(latest["metrics"]["price"]["date"], "2026-10-25")
        self.assertIn(latest["cycle"]["phase"],
                      [p for _, p in config.CYCLE_PHASES])
        self.assertEqual(latest["ticker"]["block_height"], 973093)
        self.assertIn("mvrv_zscore", latest["metrics"])
        self.assertIn("mayer_multiple", latest["metrics"])

        # Segunda corrida: solo consultas incrementales en bloque, nada completo.
        c2 = FakeClient()
        collect.run(self.tmp, client=c2)
        kinds = {k for k, _ in c2.calls}
        self.assertEqual(kinds, {"bulk"})
        self.assertLessEqual(len(c2.calls), 2)

    def test_series_files_and_scaling(self):
        collect.run(self.tmp, client=FakeClient())
        with open(collect.series_path(self.tmp, "hashrate"), encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(doc["unit"], "EH/s")
        self.assertEqual(doc["start_date"], "2010-08-24")  # día 600
        self.assertAlmostEqual(doc["values"][-1], 800, places=3)  # 8e20 H/s = 800 EH/s
        self.assertTrue(os.path.exists(collect.series_path(self.tmp, "hashrate", "csv")))

    def test_catalog_covers_published_metrics(self):
        collect.run(self.tmp, client=FakeClient())
        with open(os.path.join(self.tmp, "catalog.json"), encoding="utf-8") as fh:
            cat = json.load(fh)
        for m in cat["metrics"]:
            self.assertTrue(os.path.exists(collect.series_path(self.tmp, m["id"])), m["id"])

    def test_weight_chunks(self):
        groups = list(collect.chunks_by_weight(list(range(100)), 35))
        for g in groups:
            self.assertLessEqual(len(g) * 35 * config.WEIGHT_PER_POINT, config.MAX_REQUEST_WEIGHT)


if __name__ == "__main__":
    unittest.main()
