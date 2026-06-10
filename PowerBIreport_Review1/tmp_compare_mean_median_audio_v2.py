from pathlib import Path

from google.cloud import bigquery

OUTPUT_PATH = Path("tmp_compare_mean_median_audio_v2_result.txt")

QUERY = """
WITH stripped AS (
  SELECT
    DATE_TRUNC(DATE(TIMESTAMP_MICROS(event_timestamp)), MONTH) AS month,
    AVG(duration_sec) / 3600.0 AS mean_hour_stripped,
    APPROX_QUANTILES(duration_sec / 3600.0, 2)[OFFSET(1)] AS median_hour_stripped
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  GROUP BY 1
),
agg_country AS (
  SELECT
    month,
    country,
    num_tracks,
    total_duration_sec,
    mean_duration_sec,
    median_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
),
agg_month AS (
  SELECT
    month,
    SAFE_DIVIDE(SUM(total_duration_sec), SUM(num_tracks)) / 3600.0 AS mean_hour_agg_weighted,
    AVG(mean_duration_sec) / 3600.0 AS mean_hour_agg_unweighted,
    AVG(median_duration_sec) / 3600.0 AS median_hour_agg_avg_country_median,
    APPROX_QUANTILES(median_duration_sec / 3600.0, 2)[OFFSET(1)] AS median_hour_agg_median_country_median,
    MAX(median_duration_sec) / 3600.0 AS median_hour_agg_max_country_median,
    MIN(median_duration_sec) / 3600.0 AS median_hour_agg_min_country_median
  FROM agg_country
  GROUP BY 1
)
SELECT
  COALESCE(s.month, a.month) AS month,
  s.mean_hour_stripped,
  a.mean_hour_agg_weighted,
  a.mean_hour_agg_unweighted,
  s.median_hour_stripped,
  a.median_hour_agg_avg_country_median,
  a.median_hour_agg_median_country_median,
  a.median_hour_agg_max_country_median,
  a.median_hour_agg_min_country_median
FROM stripped s
FULL OUTER JOIN agg_month a USING (month)
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
