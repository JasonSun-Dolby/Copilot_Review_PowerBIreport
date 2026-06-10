from pathlib import Path

from google.cloud import bigquery

OUTPUT_PATH = Path("tmp_compare_mean_median_audio_result.txt")

QUERY = """
WITH stripped AS (
  SELECT
    DATE_TRUNC(DATE(TIMESTAMP_MICROS(event_timestamp)), MONTH) AS month,
    AVG(duration_sec) / 3600.0 AS mean_hour_stripped,
    APPROX_QUANTILES(duration_sec / 3600.0, 2)[OFFSET(1)] AS median_hour_stripped
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  GROUP BY 1
),
agg AS (
  SELECT
    month,
    mean_duration_sec / 3600.0 AS mean_hour_agg,
    median_duration_sec / 3600.0 AS median_hour_agg
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
),
agg_grouped AS (
  SELECT
    month,
    AVG(mean_hour_agg) AS mean_hour_agg,
    AVG(median_hour_agg) AS median_hour_agg
  FROM agg
  GROUP BY month
)
SELECT
  COALESCE(s.month, a.month) AS month,
  s.mean_hour_stripped,
  a.mean_hour_agg,
  s.mean_hour_stripped - a.mean_hour_agg AS mean_delta_hours,
  s.median_hour_stripped,
  a.median_hour_agg,
  s.median_hour_stripped - a.median_hour_agg AS median_delta_hours
FROM stripped s
FULL OUTER JOIN agg_grouped a USING (month)
ORDER BY month
"""


if __name__ == "__main__":
    client = bigquery.Client(project="ap3-prod-0e613121")
    rows = list(client.query(QUERY).result())
    lines = ["rows\t" + str(len(rows))]
    for row in rows:
        lines.append(str(dict(row.items())))
    OUTPUT_PATH.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", OUTPUT_PATH)
