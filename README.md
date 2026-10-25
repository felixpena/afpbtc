# AFPBTC — Arquitectura Financiera Personal

Backend de datos onchain y sitio de afpbtc.com.

Este backend descarga métricas onchain de Bitcoin todos los días, calcula los indicadores propios de AFPBTC y los publica como una **API estática en JSON y CSV** que lee el sitio afpbtc.com. Costo mensual: **US$0**.

```
Bitview (BRK, gratis)  ──►  GitHub Actions (1 vez al día)  ──►  rama "deploy"  ──►  Cloudflare Pages  ──►  afpbtc.com
                              collector/ + tests/                public/ + data/        (CDN gratis)
```

## Qué publica

| Ruta | Contenido |
|---|---|
| `/data/latest.json` | Último valor de cada métrica, variación a 7 y 30 días, termómetro de ciclo y ticker (comisiones y altura de bloque) |
| `/data/catalog.json` | Las métricas del panel con su explicación en español: qué mide, fórmula, cómo leerla y dónde falla |
| `/data/series/<id>.json` | Histórico diario completo de cada métrica |
| `/data/series/<id>.csv` | El mismo histórico en CSV (`date,valor`), para descargar |

Hay 26 series descargadas desde Bitview (precio, MVRV y cohortes, NUPL, SOPR y cohortes, precio realizado y cohortes, oferta LTH/STH, hashrate, dificultad, hashprice, Puell, comisión mediana, etc.) y 4 calculadas por AFPBTC:

- **MVRV Z-Score**: (Cap. de mercado − Cap. realizada) ÷ desviación estándar histórica de la Cap. de mercado.
- **Mayer Multiple**: precio ÷ media móvil de 200 días.
- **Participación LTH**: oferta de largo plazo ÷ oferta total.
- **Termómetro de ciclo AFPBTC (0–100)**: promedio del percentil histórico (desde 2012) de MVRV Z-Score, NUPL y MVRV de largo plazo. Cada día se calcula **solo con datos anteriores a esa fecha** (sin mirar el futuro).
  Referencias calculadas con datos reales: techo de dic-2017 ≈ 99, techo de abr-2021 ≈ 93, piso de nov-2022 ≈ 1,5, hoy (25-oct-2026) ≈ 38 → *Acumulación*.

## Estructura

```
collector/
  config.py    Fuente, series de Bitview, catálogo en español, fases del ciclo
  bitview.py   Cliente HTTP (solo biblioteca estándar), reintentos y pausas
  derive.py    Cálculos propios: Z-Score, Mayer, percentiles, termómetro
  collect.py   Orquesta todo y escribe public/data/
tests/         Pruebas sin internet (API simulada)
public/        Sitio estático servido por Cloudflare Pages
  index.html          Inicio: ticker, termómetro, capas, glosario, servicios, asesores
  metricas/           Panel interactivo (uPlot): ?m=<id de métrica>
  assets/             CSS, JS y uPlot (MIT) incluidos en el repo, sin CDNs
  _headers            Caché y CORS de /data
.github/workflows/collect.yml   Automatización diaria
run_local.ps1  Ejecutar y previsualizar en Windows
```

## Probar en tu computador (Windows)

1. Instala Python 3.10 o superior desde python.org (marca "Add Python to PATH").
2. En PowerShell:
   ```powershell
   cd C:\claude\afpbtc
   .\run_local.ps1
   ```
3. Abre http://localhost:8080.

Si PowerShell bloquea el script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Publicar afpbtc.com gratis

### 1. GitHub (automatización)
1. Crea un repositorio nuevo, por ejemplo `afpbtc`. Puede ser público o privado: con ~1 minuto diario de ejecución, el plan gratuito sobra en ambos casos.
2. Sube esta carpeta a la rama `main`.
3. En **Actions** verás "Datos onchain diarios". La primera ejecución parte sola con el push. También puedes lanzarla a mano con **Run workflow**.
4. Al terminar existirá la rama `deploy` con el sitio y los datos.

### 2. Cloudflare (hosting y dominio)
1. Crea una cuenta gratuita en Cloudflare y agrega el sitio `afpbtc.com` (plan Free).
2. En el registrador donde compraste el dominio, cambia los *nameservers* por los dos que te indique Cloudflare. Esto puede tardar de minutos a 24 horas.
3. En Cloudflare ve a **Workers & Pages → Create → Pages → Connect to Git** y elige el repositorio:
   - **Production branch:** `deploy`
   - **Build command:** *(vacío)*
   - **Build output directory:** `/`
4. En el proyecto, ve a **Custom domains** y agrega `afpbtc.com` y `www.afpbtc.com`. Cloudflare crea el DNS y el certificado SSL automáticamente.

Desde ahí, cada vez que el workflow publica datos, Cloudflare despliega el sitio solo (~30 despliegues al mes, dentro del límite gratuito).

## Cambiar a nodo propio

Cuando montes Bitcoin Core + BRK, no hay que tocar el código: define la variable `AFPBTC_BITVIEW_URL` (por ejemplo `http://mi-nodo:3110`) o cambia `BITVIEW_URL` en `collector/config.py`. La API es la misma.

## Buenas prácticas con la fuente

- La corrida diaria hace **1 o 2 consultas** (los últimos 35 días de todas las series en bloque). Solo la primera vez descarga cada histórico completo (~26 consultas con 1 s de pausa).
- Cada gráfico y archivo lleva la atribución "Datos: Bitview / Bitcoin Research Kit (MIT) · Cálculos: AFPBTC".
- La licencia MIT cubre el código de BRK, no necesariamente el servicio público `bitview.space`. Antes del lanzamiento comercial, conviene escribirle al mantenedor del proyecto (github.com/bitcoinresearchkit) para contarle el uso.

## Contacto

El sitio no publica direcciones de correo. Los mensajes llegan por el formulario de `/contacto/`, que envía a Formspree (con filtro anti-spam y campo trampa `_gotcha`). El ID del formulario está en el atributo `action` de `public/contacto/index.html`.

## Agregar una métrica

1. Busca la serie: `https://bitview.space/api/series/search?q=<concepto>`.
2. Agrégala a `RAW_SERIES` en `collector/config.py`. Si va al panel, agrégala también a `CATALOG` (explicación en español) y, si corresponde, a `CHART_HINTS` (zonas, línea de referencia, escala log). El panel la muestra sola.
3. Corre `python -m unittest discover -s tests` y `python -m collector.collect --full`.
