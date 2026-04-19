# yt-scraping

Refactor incremental del scraper actual hacia una herramienta de análisis de rendimiento de vídeos de YouTube.

## Qué hace esta versión

- Mantiene el scraping actual por canal o en batch.
- Sigue usando `yt_videos` como estado actual por vídeo.
- Añade snapshots históricos en `yt_video_metric_snapshots`.
- Calcula una primera capa de performance en `yt_video_performance`.
- Extrae features heurísticas de títulos en `yt_video_features`.
- Extrae transcript si hay captions disponibles y lo guarda en `yt_video_features`.
- Extrae features visuales v1 de thumbnail en `yt_video_features`.
- Mantiene la CLI compatible con `python youtube_channel_scraper.py`.
- Expone entrypoints ordenados dentro del paquete y scripts de compatibilidad en la raiz.

## Estructura

```text
src/yt_insights/
  analytics/
  clients/
  repositories/
  services/
  tools/
  cli.py
tests/
sql/
youtube_channel_scraper.py
youtube_transcript_fetcher.py
thumbnail_test.py
```

## Setup local

```bash
python -m pip install --upgrade pip
python -m pip install ".[dev]"
```

Variables de entorno soportadas:

- `YT_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## Cambios necesarios en Supabase

Antes de ejecutar el batch nuevo, crea las tablas del archivo:

```text
sql/001_youtube_analytics_schema.sql
```

Opcional para auditar ejecuciones batch:

```text
sql/002_optional_scrape_runs.sql
```

Se asume que ya existen:

- `yt_channels`
- `yt_scraper_state`
- `yt_videos`

## Ejecución

Canal puntual:

```bash
python -m yt_insights --channel-handle @handle --limit 10
```

Batch con persistencia y analytics:

```bash
python -m yt_insights --monitor-days 30 --baseline-window-days 30 --feature-workers 8 --output latest_run.json
```

Compatibilidad legacy:

```bash
python youtube_channel_scraper.py --monitor-days 30 --baseline-window-days 30 --feature-workers 8 --output latest_run.json
python youtube_transcript_fetcher.py <youtube_url_o_id>
python thumbnail_test.py <thumbnail_url_o_path>
```

## Semántica batch v1

- El scraper refresca vídeos publicados en los últimos `--monitor-days`.
- Descubre vídeos nuevos en la playlist del canal.
- Reutiliza vídeos ya conocidos en `yt_videos` dentro de esa ventana para seguir acumulando snapshots.
- Calcula baselines y ratios por canal sobre una ventana de publicación de `--baseline-window-days`.
- Descarga thumbnails y rellena `has_face`, `face_count`, `has_thumbnail_text`, `estimated_thumbnail_text_tokens`, `thumbnail_ocr_status`, `thumbnail_text`, `thumbnail_text_confidence`, `dominant_colors`, `composition_type`, `contains_chart`, `contains_map` y `visual_style`.

## Tests

```bash
pytest
```

## GitHub Actions automatico

El workflow [`.github/workflows/youtube-scraper.yml`](.github/workflows/youtube-scraper.yml) queda preparado para:

- lanzarse manualmente con `workflow_dispatch`
- ejecutarse automaticamente cada 6 horas
- subir `latest_run.json` como artefacto de cada ejecucion
- poblar `yt_videos`, `yt_video_metric_snapshots`, `yt_video_features`, `yt_video_performance` y actualizar `yt_scraper_state`

Secrets obligatorios del repositorio:

- `YT_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Repository variables opcionales:

- `SCRAPER_DEFAULT_LIMIT`
- `SCRAPER_DEFAULT_MONITOR_DAYS`
- `SCRAPER_DEFAULT_BASELINE_WINDOW_DAYS`
- `SCRAPER_DEFAULT_FEATURE_WORKERS`
- `SCRAPER_LOG_LEVEL`

Notas operativas:

- El cron de GitHub Actions esta en UTC. El workflow usa `17 */6 * * *`.
- Los tests se ejecutan en lanzamientos manuales; en las ejecuciones programadas se prioriza la ingesta automatica.
- Si quieres cambiar frecuencia o ventana de analisis, modifica el cron o las variables del repositorio sin tocar el codigo Python.
- `--feature-workers` controla el paralelismo del enriquecimiento por video. El valor por defecto es `8`.

## Limitaciones actuales

- `dominant_emotion` sigue sin extraerse; permanece `null`.
- `thumbnail_text` depende de `easyocr`; en la primera ejecucion puede necesitar descargar modelos. Usa `thumbnail_ocr_status` para distinguir `extracted`, `no_text`, `not_available`, `failed`, `no_thumbnail`, `download_failed` y `decode_failed`.
- El transcript depende de que YouTube exponga captions en la pagina del video. `transcript_status` distingue `complete`, `no_captions`, `video_unavailable`, `request_blocked`, `ip_blocked`, `dependency_missing` y `download_failed`.
- `contains_chart` y `contains_map` son heurísticas conservadoras y deben revisarse con muestra real antes de usarlas para decisiones fuertes.
- El scoring es una v1 heurística; sirve para priorizar análisis, no para automatizar decisiones finales.
- La persistencia sigue usando la REST API de Supabase vía `requests`, no el SDK.
