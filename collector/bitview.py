"""Cliente mínimo para la API de Bitview (Bitcoin Research Kit).

Solo usa la biblioteca estándar de Python, para que corra igual en Windows,
en GitHub Actions o en un nodo propio sin instalar nada.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config


class BitviewError(RuntimeError):
    pass


class BitviewClient:
    def __init__(self, base_url=None, timeout=60, retries=3, pause=None, opener=None):
        self.base_url = (base_url or config.BITVIEW_URL).rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.pause = config.REQUEST_PAUSE_SECONDS if pause is None else pause
        self._open = opener or urllib.request.urlopen
        self.requests_made = 0

    # -- HTTP -------------------------------------------------------------

    def _get(self, path, params=None):
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params, safe=",")
        req = urllib.request.Request(url, headers={
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
        })
        last_error = None
        for attempt in range(1, self.retries + 1):
            if self.requests_made and self.pause:
                time.sleep(self.pause)
            self.requests_made += 1
            try:
                with self._open(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8")
                return json.loads(body)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:300]
                # 4xx (salvo 429) no mejora reintentando.
                if 400 <= exc.code < 500 and exc.code != 429:
                    raise BitviewError(f"{exc.code} en {url}: {detail}") from exc
                last_error = BitviewError(f"{exc.code} en {url}: {detail}")
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = BitviewError(f"Fallo en {url}: {exc}")
            time.sleep(min(30, 2 ** attempt))
        raise last_error

    # -- Series -----------------------------------------------------------

    def series_range(self, series, index="day1", start=0, end=None):
        """Una serie completa o un tramo. Devuelve {'start': int, 'data': [...]}."""
        params = {"start": start}
        if end is not None:
            params["end"] = end
        resp = self._get(f"/api/series/{urllib.parse.quote(series)}/{index}", params)
        return {"start": resp["start"], "data": resp["data"]}

    def bulk(self, series_list, index="day1", start=-30):
        """Varias series en una consulta. Mantiene el orden pedido."""
        resp = self._get("/api/series/bulk", {
            "series": ",".join(series_list), "index": index, "start": start,
        })
        if not isinstance(resp, list) or len(resp) != len(series_list):
            raise BitviewError("Respuesta bulk inesperada: el número de series no coincide")
        return [{"start": r["start"], "data": r["data"]} for r in resp]

    # -- Ticker (endpoints compatibles con mempool.space) -----------------

    def fees_recommended(self):
        return self._get("/api/v1/fees/recommended")

    def tip_height(self):
        return int(self._get("/api/blocks/tip/height"))
