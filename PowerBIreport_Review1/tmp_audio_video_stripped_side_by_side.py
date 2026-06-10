from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_audio_video_stripped_side_by_side_result.txt")

q = """
WITH audio_base AS (
  SELECT
    DATE_TRUNC(DATE(TIMESTAMP_MICROS(event_timestamp)), MONTH) AS month,
    CAST(duration_sec AS FLOAT64) AS duration_sec,
    PERCENTILE_CONT(CAST(duration_sec AS FLOAT64), 0.5)
      OVER (PARTITION BY DATE_TRUNC(DATE(TIMESTAMP_MICROS(event_timestamp)), MONTH)) AS median_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
),
audio_monthly AS (
  SELECT
    month,
    MAX(duration_sec) AS audio_max_duration_sec,
    MAX(duration_sec) / 3600.0 AS audio_max_duration_hour,
    AVG(duration_sec) AS audio_mean_duration_sec,
    ANY_VALUE(median_duration_sec) AS audio_median_duration_sec
  FROM audio_base
  GROUP BY month
),
video_base AS (
  SELECT
    DATE_TRUNC(DATE(TIMESTAMP_MICROS(event_timestamp)), MONTH) AS month,
    CAST(duration_sec AS FLOAT64) AS duration_sec,
    PERCENTILE_CONT(CAST(duration_sec AS FLOAT64), 0.5)
      OVER (PARTITION BY DATE_TRUNC(DATE(TIMESTAMP_MICROS(event_timestamp)), MONTH)) AS median_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.video_recording_events_stripped`
),
video_monthly AS (
  SELECT
    month,
    MAX(duration_sec) AS video_max_duration_sec,
    MAX(duration_sec) / 3600.0 AS video_max_duration_hour,
    AVG(duration_sec) AS video_mean_duration_sec,
    ANY_VALUE(median_duration_sec) AS video_median_duration_sec
  FROM video_base
  GROUP BY month
)
SELECT
  FORMAT_DATE('%Y-%m', COALESCE(a.month, v.month)) AS month,
  a.audio_max_duration_sec,
  a.audio_max_duration_hour,
  a.audio_mean_duration_sec,
  a.audio_median_duration_sec,
  v.video_max_duration_sec,
  v.video_max_duration_hour,
  v.video_mean_duration_sec,
  v.video_median_duration_sec
FROM audio_monthly a
FULL OUTER JOIN video_monthly v
  ON a.month = v.month
ORDER BY month
"""

c = bigquery.Client(project="ap3-prod-0e613121")
rows = list(c.query(q).result())

lines = ["rows\t" + str(len(rows))]
for r in rows:
    lines.append(str(dict(r.items())))

out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
print("wrote", out)
