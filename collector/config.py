"""Configuración del recolector AFPBTC.

Cada métrica del panel se define una sola vez aquí: de qué serie de Bitview
sale, cómo se escala y cómo se explica en español. El catálogo público
(`data/catalog.json`) se genera a partir de esta lista.
"""

from datetime import date

# --- Fuente de datos -------------------------------------------------------

# Instancia pública y gratuita del Bitcoin Research Kit (BRK, licencia MIT).
# Cuando AFPBTC tenga su propio nodo con BRK, basta con cambiar esta URL
# (o definir la variable de entorno AFPBTC_BITVIEW_URL).
BITVIEW_URL = "https://bitview.space"

# Respaldo para el ticker en vivo (API compatible con mempool.space).
MEMPOOL_URL = "https://mempool.space"

USER_AGENT = "afpbtc-collector/1.0 (+https://afpbtc.com)"

# El índice "day1" de BRK cuenta días desde esta fecha (día 0 = 2009-01-01).
DAY1_EPOCH = date(2009, 1, 1)

# Bitview rechaza consultas con "peso" > 320.000. Cada punto pesa ~13,
# así que una serie completa (~6.500 días) cabe sola, pero no varias juntas.
MAX_REQUEST_WEIGHT = 320_000
WEIGHT_PER_POINT = 13

# En cada corrida diaria se vuelven a pedir los últimos N días de todas las
# series en UNA sola consulta (corrige el día en curso, que viene parcial).
INCREMENTAL_DAYS = 35

# Pausa entre consultas, para ser buen vecino con la instancia pública.
REQUEST_PAUSE_SECONDS = 1.0

# Los primeros años tienen precios poco representativos; los percentiles del
# termómetro de ciclo solo consideran datos desde esta fecha.
CYCLE_BASELINE_START = date(2012, 1, 1)

ATTRIBUTION = "Datos: Bitview / Bitcoin Research Kit (MIT) · Cálculos: AFPBTC"


# --- Series que se descargan desde Bitview --------------------------------
# id: nombre del archivo publicado (data/series/<id>.json)
# series: identificador exacto en Bitview (verificado en bitview.space/api)
# scale: divisor aplicado al valor original (p. ej. H/s -> EH/s)

RAW_SERIES = [
    # Precio y valoración
    {"id": "price", "series": "price", "unit": "USD", "scale": 1},
    {"id": "market_cap", "series": "market_cap", "unit": "USD", "scale": 1},
    {"id": "realized_cap", "series": "realized_cap", "unit": "USD", "scale": 1},
    {"id": "realized_price", "series": "realized_price", "unit": "USD", "scale": 1},
    {"id": "lth_realized_price", "series": "lth_realized_price", "unit": "USD", "scale": 1},
    {"id": "sth_realized_price", "series": "sth_realized_price", "unit": "USD", "scale": 1},
    {"id": "price_sma_200d", "series": "price_sma_200d", "unit": "USD", "scale": 1},
    {"id": "price_sma_200w", "series": "price_sma_200w", "unit": "USD", "scale": 1},
    {"id": "mvrv", "series": "mvrv", "unit": "ratio", "scale": 1},
    {"id": "lth_mvrv", "series": "lth_mvrv", "unit": "ratio", "scale": 1},
    {"id": "sth_mvrv", "series": "sth_mvrv", "unit": "ratio", "scale": 1},
    # Comportamiento
    {"id": "nupl", "series": "nupl", "unit": "ratio", "scale": 1},
    {"id": "sopr", "series": "sopr_24h", "unit": "ratio", "scale": 1},
    {"id": "asopr", "series": "asopr_24h", "unit": "ratio", "scale": 1},
    {"id": "lth_sopr", "series": "lth_sopr_24h", "unit": "ratio", "scale": 1},
    {"id": "sth_sopr", "series": "sth_sopr_24h", "unit": "ratio", "scale": 1},
    {"id": "reserve_risk", "series": "reserve_risk", "unit": "ratio", "scale": 1},
    # Holders
    {"id": "supply", "series": "supply", "unit": "BTC", "scale": 1},
    {"id": "lth_supply", "series": "lth_supply", "unit": "BTC", "scale": 1},
    {"id": "sth_supply", "series": "sth_supply", "unit": "BTC", "scale": 1},
    {"id": "supply_in_profit", "series": "supply_in_profit", "unit": "BTC", "scale": 1},
    # Red y minería
    {"id": "hashrate", "series": "hash_rate_sma_1w", "unit": "EH/s", "scale": 1e18},
    {"id": "difficulty", "series": "difficulty", "unit": "T", "scale": 1e12},
    {"id": "hashprice", "series": "hash_price_phs", "unit": "USD/PH/día", "scale": 1},
    {"id": "puell_multiple", "series": "puell_multiple", "unit": "ratio", "scale": 1},
    # Mempool
    {"id": "fee_rate_median", "series": "effective_fee_rate_median", "unit": "sat/vB", "scale": 1},
]


# --- Catálogo público (lo que ve el usuario en el panel) -------------------
# source: "bitview" = serie descargada; "afpbtc" = calculada por AFPBTC.

GROUPS = ["Valoración", "Comportamiento", "Holders", "Red", "Mempool", "Ciclo"]

CATALOG = [
    {
        "id": "mvrv_zscore", "group": "Valoración", "name": "MVRV Z-Score",
        "unit": "σ", "source": "afpbtc",
        "what": "Qué tan lejos está el valor de mercado de su valor realizado, en desviaciones estándar.",
        "formula": "(Cap. de mercado − Cap. realizada) ÷ desviación estándar histórica de la Cap. de mercado",
        "read": "Valores altos han coincidido con techos de ciclo; valores bajos o negativos, con zonas de acumulación.",
        "limits": "Los umbrales históricos se desplazan a medida que madura el mercado y entra capital institucional.",
    },
    {
        "id": "mvrv", "group": "Valoración", "name": "MVRV", "unit": "×", "source": "bitview",
        "what": "Precio de mercado dividido por el precio realizado (costo base promedio de la red).",
        "formula": "Precio ÷ Precio realizado",
        "read": "Sobre 1, el holder promedio está en ganancia; bajo 1, en pérdida.",
        "limits": "Monedas perdidas y custodia en exchanges distorsionan el costo base real.",
    },
    {
        "id": "realized_price", "group": "Valoración", "name": "Precio realizado", "unit": "USD",
        "source": "bitview",
        "what": "El costo base promedio de todos los bitcoins según su último movimiento.",
        "formula": "Capitalización realizada ÷ oferta circulante",
        "read": "Cuando el precio cae bajo el realizado, el holder promedio está en pérdida.",
        "limits": "Monedas perdidas y custodia en exchanges distorsionan el costo base real.",
    },
    {
        "id": "mayer_multiple", "group": "Valoración", "name": "Mayer Multiple", "unit": "×",
        "source": "afpbtc",
        "what": "El precio relativo a su media móvil de 200 días.",
        "formula": "Precio ÷ media móvil simple de 200 días",
        "read": "Mide estiramiento respecto de la tendencia de largo plazo.",
        "limits": "Es una métrica de precio, no estrictamente onchain.",
    },
    {
        "id": "sopr", "group": "Comportamiento", "name": "SOPR", "unit": "×", "source": "bitview",
        "what": "Si las monedas que se mueven hoy se venden con ganancia o con pérdida.",
        "formula": "Valor en USD al gastarse ÷ valor en USD al crearse el output (24 h)",
        "read": "Sobre 1 se realiza ganancia; bajo 1, pérdida. El 1 suele actuar como soporte en alzas.",
        "limits": "Movimientos internos de exchanges y custodios agregan ruido.",
    },
    {
        "id": "nupl", "group": "Comportamiento", "name": "NUPL", "unit": "ratio", "source": "bitview",
        "what": "La ganancia o pérdida no realizada de la red como fracción de su valor.",
        "formula": "(Cap. de mercado − Cap. realizada) ÷ Cap. de mercado",
        "read": "Se lee por fases: capitulación, esperanza, optimismo, creencia y euforia.",
        "limits": "Comparte las debilidades del precio realizado.",
    },
    {
        "id": "reserve_risk", "group": "Comportamiento", "name": "Reserve Risk", "unit": "ratio",
        "source": "bitview",
        "what": "Confianza de los holders de largo plazo frente al precio actual.",
        "formula": "Precio ÷ costo de oportunidad acumulado de no gastar monedas antiguas",
        "read": "Valores bajos indican alta convicción y precio atractivo en perspectiva histórica.",
        "limits": "Depende de supuestos sobre el comportamiento de monedas dormidas.",
    },
    {
        "id": "lth_supply", "group": "Holders", "name": "Oferta LTH", "unit": "BTC", "source": "bitview",
        "what": "Bitcoins en manos de largo plazo (UTXO de 150 días o más).",
        "formula": "Suma de UTXO con edad ≥ 150 días",
        "read": "Los holders de largo plazo tienden a distribuir en alzas y acumular en caídas.",
        "limits": "El umbral de 150 días es una convención, no una ley.",
    },
    {
        "id": "sth_supply", "group": "Holders", "name": "Oferta STH", "unit": "BTC", "source": "bitview",
        "what": "Bitcoins en manos de corto plazo (UTXO de menos de 150 días).",
        "formula": "Suma de UTXO con edad < 150 días",
        "read": "Crece cuando entran compradores nuevos o se reactivan monedas antiguas.",
        "limits": "No distingue entre una venta y un cambio de billetera.",
    },
    {
        "id": "hashrate", "group": "Red", "name": "Hashrate", "unit": "EH/s", "source": "bitview",
        "what": "El poder de cómputo total que asegura la red.",
        "formula": "Estimado desde dificultad y bloques producidos (media de 7 días)",
        "read": "Tendencia alcista = más seguridad y compromiso de los mineros.",
        "limits": "Es una estimación; varía con la suerte de los bloques.",
    },
    {
        "id": "hashprice", "group": "Red", "name": "Hashprice", "unit": "USD/PH/día", "source": "bitview",
        "what": "Ingreso esperado de un minero por unidad de poder de cómputo.",
        "formula": "Ingreso de mineros en 24 h ÷ hashrate",
        "read": "Hashprice bajo presiona a los mineros menos eficientes.",
        "limits": "Sensible a picos de comisiones y al precio.",
    },
    {
        "id": "puell_multiple", "group": "Red", "name": "Puell Multiple", "unit": "×", "source": "bitview",
        "what": "Ingreso diario por emisión comparado con su promedio de un año.",
        "formula": "Valor USD de la emisión diaria ÷ media de 365 días",
        "read": "Valores bajos han coincidido con capitulación minera; altos, con euforia.",
        "limits": "Los halvings cambian la escala de la emisión.",
    },
    {
        "id": "fee_rate_median", "group": "Mempool", "name": "Comisión mediana", "unit": "sat/vB",
        "source": "bitview",
        "what": "Lo que pagan los usuarios por entrar en un bloque.",
        "formula": "Mediana de la tasa efectiva de comisión del día",
        "read": "Picos señalan demanda de espacio de bloque.",
        "limits": "Eventos puntuales (inscripciones, consolidaciones) generan picos aislados.",
    },
    {
        "id": "cycle_index", "group": "Ciclo", "name": "Termómetro de ciclo AFPBTC", "unit": "0–100",
        "source": "afpbtc",
        "what": "Índice compuesto que ubica el mercado entre capitulación (0) y euforia (100).",
        "formula": "Promedio del percentil histórico (desde 2012) de MVRV Z-Score, NUPL y MVRV de largo plazo",
        "read": "0–20 capitulación · 20–40 acumulación · 40–60 optimismo · 60–80 creencia · 80–100 euforia.",
        "limits": "Es descriptivo, no predictivo. Los percentiles usan solo datos pasados a cada fecha.",
    },
]

CATALOG += [
    {
        "id": "lth_mvrv", "group": "Valoración", "name": "MVRV de largo plazo", "unit": "×",
        "source": "bitview",
        "what": "Ganancia no realizada de los holders de largo plazo (150 días o más).",
        "formula": "Precio ÷ precio realizado de los holders de largo plazo",
        "read": "Mide la convicción de las manos fuertes: valores altos indican grandes ganancias acumuladas que pueden empezar a venderse.",
        "limits": "El grupo cambia de composición a medida que monedas cumplen 150 días.",
    },
    {
        "id": "sth_mvrv", "group": "Valoración", "name": "MVRV de corto plazo", "unit": "×",
        "source": "bitview",
        "what": "Ganancia o pérdida de los compradores recientes (menos de 150 días).",
        "formula": "Precio ÷ precio realizado de los holders de corto plazo",
        "read": "Bajo 1, los compradores recientes están en pérdida; el nivel 1 suele actuar como soporte o resistencia.",
        "limits": "Reacciona rápido al precio y genera señales falsas en mercados laterales.",
    },
    {
        "id": "lth_share", "group": "Holders", "name": "Participación LTH", "unit": "%",
        "source": "afpbtc",
        "what": "Porcentaje de la oferta en manos de largo plazo.",
        "formula": "Oferta LTH ÷ oferta total × 100",
        "read": "Sube en mercados bajistas (acumulación) y baja cuando los holders antiguos distribuyen en alzas.",
        "limits": "Hereda la convención de 150 días de la definición LTH.",
    },
]

# Pistas para los gráficos del panel: zonas históricas (high/low), línea de
# referencia (ref), escala logarítmica (log) y si comparte eje con el precio.
CHART_HINTS = {
    "mvrv_zscore": {"high": 7, "low": 0},
    "mvrv": {"high": 3.5, "low": 1, "ref": 1},
    "lth_mvrv": {"ref": 1, "log": True},
    "sth_mvrv": {"ref": 1},
    "realized_price": {"same_axis_as_price": True, "log": True},
    "mayer_multiple": {"high": 2.4, "low": 0.8, "ref": 1},
    "sopr": {"ref": 1},
    "nupl": {"high": 0.75, "low": 0, "ref": 0},
    "reserve_risk": {"high": 0.02, "low": 0.0015, "log": True},
    "hashrate": {"log": True},
    "hashprice": {"log": True},
    "puell_multiple": {"high": 4, "low": 0.5, "ref": 1},
    "fee_rate_median": {"log": True},
    "cycle_index": {"high": 80, "low": 20, "min": 0, "max": 100},
}

CYCLE_PHASES = [
    (20, "Capitulación"),
    (40, "Acumulación"),
    (60, "Optimismo"),
    (80, "Creencia"),
    (101, "Euforia"),
]
