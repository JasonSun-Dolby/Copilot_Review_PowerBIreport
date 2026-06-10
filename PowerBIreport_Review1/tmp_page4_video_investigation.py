from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_page4_video_investigation_result.txt")

PROJECT = "ap3-prod-0e613121"
DATASET = "analytics_184529778"

TARGET_HIST = {
    "0-1m":   0.6348252918043011,
    "1-5m":   0.32599099912657215,
    "5-10m":  0.026593265266576512,
    "10-15m": 0.005503870770529566,
    "15-20m": 0.0023010277485103797,
    "20-25m": 0.0012967708677462395,
    "25-30m": 0.0007738661174589709,
    "0.5-1h": 0.0019036036818089624,
    "1-8h":   0.0008014307266401251,
    "8-24h":  0.000008639653623943854,
    ">24h":   0.0000012342362319919791,
}
BIN_ORDER = list(TARGET_HIST.keys())

# 1. Schema of monthly_video_recordings_aggregated
Q_SCHEMA_VID_AGG = f"""
SELECT column_name, data_type
FROM `{PROJECT}.{DATASET}`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'monthly_video_recordings_aggregated'
ORDER BY ordinal_position
"""

# 2. Sample raw values (mean/median) from aggregated table to check units
Q_SAMPLE_AGG = f"""
SELECT month, country, num_tracks,
       mean_duration_sec, median_duration_sec, total_duration_sec
FROM `{PROJECT}.{DATASET}.monthly_video_recordings_aggregated`
WHERE month = DATE '2025-11-01'
ORDER BY num_tracks DESC
LIMIT 5
"""

# 3. Ratio check: if mean from chart (17459 sec) vs BQ (93.37 sec) -> ratio ~187x
# Check if duration_sec in video table is actually in milliseconds
Q_RATIO = f"""
SELECT
  FORMAT_DATE('%Y-%m', month) AS month,
  AVG(mean_duration_sec) AS avg_mean_sec,
  AVG(mean_duration_sec) / 3600.0 AS avg_mean_hr,
  AVG(mean_duration_sec) * 1000.0 AS avg_mean_ms,
  -- try treating the column as milliseconds
  AVG(mean_duration_sec) / 1000.0 AS avg_mean_if_ms_to_sec,
  -- what ratio matches chart value of 17459 sec for 2025-11?
  17459.998 / AVG(CASE WHEN FORMAT_DATE('%Y-%m', month) = '2025-11' THEN mean_duration_sec END) AS ratio_to_target
FROM `{PROJECT}.{DATASET}.monthly_video_recordings_aggregated`
WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
GROUP BY 1
ORDER BY 1
"""

# 4. Check if there's a video_recording_events_stripped equivalent
Q_LIST = f"""
SELECT table_name
FROM `{PROJECT}.{DATASET}`.INFORMATION_SCHEMA.TABLES
WHERE LOWER(table_name) LIKE '%video%'
ORDER BY table_name
"""

# 5. Histogram from video_duration_view with cutoff at same boundary as audio (~2026-05-29 21:00 UTC)
Q_HIST_CUTOFF = f"""
WITH base AS (
  SELECT
    CASE
      WHEN duration_sec < 60 THEN '0-1m'
      WHEN duration_sec < 300 THEN '1-5m'
      WHEN duration_sec < 600 THEN '5-10m'
      WHEN duration_sec < 900 THEN '10-15m'
      WHEN duration_sec < 1200 THEN '15-20m'
      WHEN duration_sec < 1500 THEN '20-25m'
      WHEN duration_sec < 1800 THEN '25-30m'
      WHEN duration_sec < 3600 THEN '0.5-1h'
      WHEN duration_sec < 28800 THEN '1-8h'
      WHEN duration_sec < 86400 THEN '8-24h'
      ELSE '>24h'
    END AS bin,
    COUNT(*) AS cnt
  FROM `{PROJECT}.{DATASET}.video_duration_view`
  WHERE TIMESTAMP_MICROS(event_timestamp) < TIMESTAMP '2026-05-29 21:00:00+00'
  GROUP BY 1
),
tot AS (SELECT SUM(cnt) AS total FROM base)
SELECT bin, cnt, SAFE_DIVIDE(cnt, total) AS pct
FROM base, tot
ORDER BY CASE bin
  WHEN '0-1m' THEN 1 WHEN '1-5m' THEN 2 WHEN '5-10m' THEN 3
  WHEN '10-15m' THEN 4 WHEN '15-20m' THEN 5 WHEN '20-25m' THEN 6
  WHEN '25-30m' THEN 7 WHEN '0.5-1h' THEN 8 WHEN '1-8h' THEN 9
  WHEN '8-24h' THEN 10 WHEN '>24h' THEN 11 ELSE 99
END
"""


if __name__ == "__main__":
    c = bigquery.Client(project=PROJECT)
    lines = []

    lines.append("===SCHEMA monthly_video_recordings_aggregated===")
    for r in c.query(Q_SCHEMA_VID_AGG).result():
        lines.append(f"  {r.column_name}\t{r.data_type}")

    lines.append("===SAMPLE monthly_video_recordings_aggregated (Nov 2025 top 5)===")
    for r in c.query(Q_SAMPLE_AGG).result():
        lines.append(str(dict(r.items())))

    lines.append("===RATIO CHECK===")
    for r in c.query(Q_RATIO).result():
        lines.append(str(dict(r.items())))

    lines.append("===VIDEO TABLES===")
    for r in c.query(Q_LIST).result():
        lines.append(f"  {r.table_name}")

    lines.append("===HIST from video_duration_view with cutoff===")
    bq_hist = {}
    for r in c.query(Q_HIST_CUTOFF).result():
        bq_hist[r.bin] = float(r.pct)
        lines.append(f"  {r.bin}: pct={float(r.pct):.10g}  delta={float(r.pct)-TARGET_HIST.get(r.bin, 0):.6g}")

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)
