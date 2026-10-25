"""Métricas calculadas por AFPBTC a partir de las series de Bitview.

Todas las funciones trabajan con listas alineadas por día (índice day1 de
BRK) donde los días sin dato son None. Ningún cálculo usa información del
futuro: cada valor se calcula solo con datos disponibles hasta esa fecha.
"""

import bisect
import math

from . import config


def _ok(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def ratio(numerator, denominator):
    out = []
    for a, b in zip(numerator, denominator):
        out.append(a / b if _ok(a) and _ok(b) and b != 0 else None)
    return out


def mvrv_zscore(market_cap, realized_cap, min_points=365):
    """(MC − RC) / desviación estándar expandida de MC (algoritmo de Welford)."""
    out = []
    n, mean, m2 = 0, 0.0, 0.0
    for mc, rc in zip(market_cap, realized_cap):
        if _ok(mc):
            n += 1
            delta = mc - mean
            mean += delta / n
            m2 += delta * (mc - mean)
        if _ok(mc) and _ok(rc) and n >= min_points:
            std = math.sqrt(m2 / n)
            out.append((mc - rc) / std if std > 0 else None)
        else:
            out.append(None)
    return out


def expanding_percentile(values, start_index=0, min_points=365):
    """Percentil (0–1) de cada valor frente a todos los valores previos desde start_index."""
    out = [None] * len(values)
    seen = []
    for i in range(start_index, len(values)):
        x = values[i]
        if not _ok(x):
            continue
        bisect.insort(seen, x)
        if len(seen) >= min_points:
            lo = bisect.bisect_left(seen, x)
            hi = bisect.bisect_right(seen, x)
            out[i] = ((lo + hi) / 2) / len(seen)
    return out


def cycle_index(component_series, start_index):
    """Promedio de percentiles expandidos de cada componente, en escala 0–100."""
    pct = [expanding_percentile(s, start_index) for s in component_series]
    out = []
    for parts in zip(*pct):
        if all(p is not None for p in parts):
            out.append(100 * sum(parts) / len(parts))
        else:
            out.append(None)
    return out


def phase(value):
    if not _ok(value):
        return None
    for limit, name in config.CYCLE_PHASES:
        if value < limit:
            return name
    return config.CYCLE_PHASES[-1][1]


def last_valid(values):
    for i in range(len(values) - 1, -1, -1):
        if _ok(values[i]):
            return i, values[i]
    return None, None


def change(values, days):
    """Variación porcentual del último valor válido frente a `days` días antes."""
    i, v = last_valid(values)
    if i is None or i - days < 0:
        return None
    prev = values[i - days]
    if not _ok(prev) or prev == 0:
        return None
    return (v - prev) / abs(prev) * 100
