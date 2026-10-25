"""Recolector diario de AFPBTC.

Uso:
    python -m collector.collect               # actualización incremental
    python -m collector.collect --full        # vuelve a descargar todo el histórico
    python -m collector.collect --out public/data

Genera una "API estática" que el sitio afpbtc.com lee directamente:
    data/latest.json            último valor de cada métrica + ticker + ciclo
    data/catalog.json           métricas, explicaciones en español y fuentes
    data/series/<id>.json       histórico diario completo
    data/series/<id>.csv        el mismo histórico en CSV (fecha,valor)
"""

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

from . import config, derive
from .bitview import BitviewClient, BitviewError


# --- utilidades -------------------------------------------------------------

def day_to_date(i):
    return (config.DAY1_EPOCH + timedelta(days=i)).isoformat()


def date_to_day(s):
    return (datetime.strptime(s, "%Y-%m-%d").date() - config.DAY1_EPOCH).days


def sig(x, digits=6):
    """Redondea a `digits` cifras significativas para achicar los archivos."""
    if x is None or not isinstance(x, (int, float)) or not math.isfinite(x):
        return None
    if x == 0:
        return 0
    return round(x, -int(math.floor(math.log10(abs(x)))) + (digits - 1))


def log(msg):
    print(msg, flush=True)


# --- almacenamiento ---------------------------------------------------------

def series_path(out_dir, sid, ext="json"):
    return os.path.join(out_dir, "series", f"{sid}.{ext}")


def load_series(out_dir, sid):
    """Devuelve la serie alineada desde el día 0, o None si no existe."""
    path = series_path(out_dir, sid)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    offset = date_to_day(doc["start_date"])
    return [None] * offset + list(doc["values"])


def write_series(out_dir, sid, values, unit, source, updated):
    first = next((i for i, v in enumerate(values) if v is not None), None)
    if first is None:
        return False
    trimmed = [sig(v) for v in values[first:]]
    doc = {
        "id": sid,
        "unit": unit,
        "source": source,
        "index": "day1",
        "start_date": day_to_date(first),
        "end_date": day_to_date(len(values) - 1),
        "updated": updated,
        "attribution": config.ATTRIBUTION,
        "values": trimmed,
    }
    os.makedirs(os.path.join(out_dir, "series"), exist_ok=True)
    tmp = series_path(out_dir, sid) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, series_path(out_dir, sid))

    with open(series_path(out_dir, sid, "csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", sid])
        for k, v in enumerate(trimmed):
            w.writerow([day_to_date(first + k), "" if v is None else v])
    return True


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# --- descarga ---------------------------------------------------------------

def scaled(data, scale):
    if scale == 1:
        return list(data)
    return [None if v is None else v / scale for v in data]


def merge(existing, start, chunk):
    values = list(existing or [])
    need = start + len(chunk)
    if len(values) < need:
        values.extend([None] * (need - len(values)))
    for k, v in enumerate(chunk):
        values[start + k] = v
    return values


def chunks_by_weight(items, days):
    per_series = days * config.WEIGHT_PER_POINT
    size = max(1, config.MAX_REQUEST_WEIGHT // per_series)
    for i in range(0, len(items), size):
        yield items[i:i + size]


def fetch_raw(client, out_dir, full=False):
    """Descarga/actualiza todas las RAW_SERIES. Devuelve {id: valores}."""
    series = {}
    pending_incremental = []

    for spec in config.RAW_SERIES:
        existing = None if full else load_series(out_dir, spec["id"])
        if existing is None:
            log(f"  histórico completo: {spec['series']}")
            try:
                r = client.series_range(spec["series"], start=0)
            except BitviewError as exc:
                if spec["id"] == "price":
                    raise
                log(f"  ! se omite {spec['id']}: {exc}")
                continue
            series[spec["id"]] = merge(None, r["start"], scaled(r["data"], spec["scale"]))
        else:
            series[spec["id"]] = existing
            pending_incremental.append(spec)

    for group in chunks_by_weight(pending_incremental, config.INCREMENTAL_DAYS):
        log(f"  incremental ({config.INCREMENTAL_DAYS} días): {len(group)} series en 1 consulta")
        results = client.bulk([s["series"] for s in group], start=-config.INCREMENTAL_DAYS)
        for spec, r in zip(group, results):
            series[spec["id"]] = merge(series[spec["id"]], r["start"],
                                       scaled(r["data"], spec["scale"]))
    return series


def fetch_ticker(client):
    """Comisiones y altura de bloque. Si Bitview falla, prueba mempool.space."""
    ticker = {}
    for c in (client, BitviewClient(base_url=config.MEMPOOL_URL, retries=1)):
        try:
            ticker["fees"] = c.fees_recommended()
            ticker["block_height"] = c.tip_height()
            ticker["source"] = c.base_url
            return ticker
        except BitviewError as exc:
            log(f"  ! ticker no disponible en {c.base_url}: {exc}")
    return ticker


# --- armado de la salida ----------------------------------------------------

def build(series):
    """Agrega las métricas calculadas por AFPBTC."""
    d = dict(series)
    if "market_cap" in d and "realized_cap" in d:
        d["mvrv_zscore"] = derive.mvrv_zscore(d["market_cap"], d["realized_cap"])
    if "price" in d and "price_sma_200d" in d:
        d["mayer_multiple"] = derive.ratio(d["price"], d["price_sma_200d"])
    if "lth_supply" in d and "supply" in d:
        d["lth_share"] = [None if v is None else v * 100 for v in derive.ratio(d["lth_supply"], d["supply"])]

    comps = [d.get("mvrv_zscore"), d.get("nupl"), d.get("lth_mvrv")]
    if all(c is not None for c in comps):
        n = min(len(c) for c in comps)
        start = (config.CYCLE_BASELINE_START - config.DAY1_EPOCH).days
        d["cycle_index"] = derive.cycle_index([c[:n] for c in comps], start)
    return d


def units():
    u = {s["id"]: (s["unit"], "bitview") for s in config.RAW_SERIES}
    u.update({
        "mvrv_zscore": ("σ", "afpbtc"),
        "mayer_multiple": ("×", "afpbtc"),
        "lth_share": ("%", "afpbtc"),
        "cycle_index": ("0–100", "afpbtc"),
    })
    return u


def latest_doc(d, ticker, generated):
    metrics = {}
    for sid, values in d.items():
        i, v = derive.last_valid(values)
        if i is None:
            continue
        metrics[sid] = {
            "value": sig(v),
            "date": day_to_date(i),
            "change_7d_pct": sig(derive.change(values, 7), 4),
            "change_30d_pct": sig(derive.change(values, 30), 4),
        }
    cyc = metrics.get("cycle_index")
    return {
        "generated_at": generated,
        "attribution": config.ATTRIBUTION,
        "cycle": {
            "value": cyc["value"] if cyc else None,
            "phase": derive.phase(cyc["value"]) if cyc else None,
            "date": cyc["date"] if cyc else None,
        },
        "ticker": ticker,
        "metrics": metrics,
    }


def catalog_doc(generated):
    u = units()
    items = []
    for m in config.CATALOG:
        item = dict(m)
        item["series_url"] = f"/data/series/{m['id']}.json"
        item["csv_url"] = f"/data/series/{m['id']}.csv"
        item["source_label"] = ("Calculado por AFPBTC con datos de Bitview"
                                if m["source"] == "afpbtc" else "Bitview / BRK")
        item.setdefault("unit", u.get(m["id"], ("", ""))[0])
        items.append(item)
    return {"generated_at": generated, "groups": config.GROUPS,
            "attribution": config.ATTRIBUTION, "metrics": items}


def run(out_dir, full=False, client=None):
    client = client or BitviewClient(base_url=os.environ.get("AFPBTC_BITVIEW_URL"))
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    log(f"AFPBTC · recolector · {generated} · fuente {client.base_url}")
    raw = fetch_raw(client, out_dir, full=full)
    data = build(raw)

    u = units()
    written = 0
    for sid, values in data.items():
        unit, source = u.get(sid, ("", "afpbtc"))
        written += write_series(out_dir, sid, values, unit, source, generated)

    ticker = fetch_ticker(client)
    write_json(os.path.join(out_dir, "latest.json"), latest_doc(data, ticker, generated))
    write_json(os.path.join(out_dir, "catalog.json"), catalog_doc(generated))

    log(f"Listo: {written} series, {client.requests_made} consultas a la API.")
    return data


def main(argv=None):
    p = argparse.ArgumentParser(description="Recolector de datos onchain de AFPBTC")
    p.add_argument("--out", default=os.path.join("public", "data"),
                   help="carpeta de salida (por defecto public/data)")
    p.add_argument("--full", action="store_true",
                   help="descarga nuevamente todo el histórico")
    args = p.parse_args(argv)
    try:
        run(args.out, full=args.full)
    except BitviewError as exc:
        log(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
