from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_page4_video_validation_result.txt")

PROJECT = "ap3-prod-0e613121"
DATASET = "analytics_184529778"

# What Page 4 actually shows (extracted from live visuals)
TARGET_MAX = {
    "2025-11": 10.271544444444444,
    "2025-12": 9.757368611111112,
    "2026-01": 28.50047309027778,
    "2026-02": 5.834038888888889,
    "2026-03": 6.2034488888888895,
    "2026-04": 9.574871961805556,
    "2026-05": 28.014227430555554,
}
TARGET_MEAN = {
    "2025-11": 17459.997999148138,
    "2025-12": 16177.214932289435,
    "2026-01": 16836.353791522994,
    "2026-02": 18035.408259434982,
    "2026-03": 17683.90961640899,
    "2026-04": 18922.289632443997,
    "2026-05": 19653.398656084843,
}
TARGET_MEDIAN = {
    "2025-11": 9085.549492750884,
    "2025-12": 8088.3677750554825,
    "2026-01": 8209.920223385485,
    "2026-02": 9378.13563824884,
    "2026-03": 8606.057599144346,
    "2026-04": 8589.370711601288,
    "2026-05": 9803.517588534389,
}
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

Q_MAX = f"""
SELECT
  FORMAT_DATE('%Y-%m', month) AS month,
  MAX(max_duration_sec) / 3600.0 AS max_duration_hour
FROM `{PROJECT}.{DATASET}.monthly_video_recordings_aggregated`
WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
GROUP BY 1
ORDER BY 1
"""

Q_MEAN_MEDIAN = f"""
WITH x AS (
  SELECT
    month,
    mean_duration_sec,
    median_duration_sec,
    PERCENTILE_CONT(median_duration_sec, 0.5) OVER (PARTITION BY month) AS p50
  FROM `{PROJECT}.{DATASET}.monthly_video_recordings_aggregated`
  WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
)
SELECT
  FORMAT_DATE('%Y-%m', month) AS month,
  AVG(mean_duration_sec) AS Mean_duration_sec,
  ANY_VALUE(p50) AS Median_duration_sec
FROM x
GROUP BY 1
ORDER BY 1
"""

# Find video stripped/events source table
Q_LIST_VIDEO_TABLES = f"""
SELECT table_name
FROM `{PROJECT}.{DATASET}`.INFORMATION_SCHEMA.TABLES
WHERE LOWER(table_name) LIKE '%video%recording%event%'
   OR LOWER(table_name) LIKE '%video%duration%'
ORDER BY table_name
"""

Q_HIST_FROM_AGG = f"""
WITH rows_per_country AS (
  SELECT
    month,
    country,
    num_tracks,
    CASE
      WHEN mean_duration_sec < 60 THEN '0-1m'
      WHEN mean_duration_sec < 300 THEN '1-5m'
      WHEN mean_duration_sec < 600 THEN '5-10m'
      WHEN mean_duration_sec < 900 THEN '10-15m'
      WHEN mean_duration_sec < 1200 THEN '15-20m'
      WHEN mean_duration_sec < 1500 THEN '20-25m'
      WHEN mean_duration_sec < 1800 THEN '25-30m'
      WHEN mean_duration_sec < 3600 THEN '0.5-1h'
      WHEN mean_duration_sec < 28800 THEN '1-8h'
      WHEN mean_duration_sec < 86400 THEN '8-24h'
      ELSE '>24h'
    END AS bin
  FROM `{PROJECT}.{DATASET}.monthly_video_recordings_aggregated`
),
bins AS (
  SELECT bin, SUM(num_tracks) AS cnt
  FROM rows_per_country
  GROUP BY bin
),
tot AS (SELECT SUM(cnt) AS total FROM bins)
SELECT bin, cnt, SAFE_DIVIDE(cnt, total) AS pct
FROM bins, tot
ORDER BY CASE bin
  WHEN '0-1m' THEN 1 WHEN '1-5m' THEN 2 WHEN '5-10m' THEN 3
  WHEN '10-15m' THEN 4 WHEN '15-20m' THEN 5 WHEN '20-25m' THEN 6
  WHEN '25-30m' THEN 7 WHEN '0.5-1h' THEN 8 WHEN '1-8h' THEN 9
  WHEN '8-24h' THEN 10 WHEN '>24h' THEN 11 ELSE 99
END
"""

# Also check the video_duration_view schema
Q_VIDEO_VIEW_SCHEMA = f"""
SELECT column_name, data_type
FROM `{PROJECT}.{DATASET}`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'video_duration_view'
ORDER BY ordinal_position
"""

Q_HIST_FROM_VIDEO_VIEW = f"""
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


def compare_dict(label, bq_dict, target_dict):
    lines = [f"--- {label} ---"]
    match = True
    for k in target_dict:
        bq_val = bq_dict.get(k, float("nan"))
        delta = bq_val - target_dict[k]
        flag = "" if abs(delta) < 1e-4 else "  *** MISMATCH"
        if abs(delta) >= 1e-4:
            match = False
        lines.append(f"  {k}: bq={bq_val:.10g}  powerbi={target_dict[k]:.10g}  delta={delta:.6g}{flag}")
    lines.append(f"  OVERALL: {'MATCH' if match else 'MISMATCH'}")
    return lines


if __name__ == "__main__":
    c = bigquery.Client(project=PROJECT)
    lines = []

    # 1. Max by month
    rows = list(c.query(Q_MAX).result())
    bq_max = {r.month: float(r.max_duration_hour) for r in rows}
    lines += compare_dict("MAX DURATION (hours) by month vs monthly_video_recordings_aggregated", bq_max, TARGET_MAX)

    # 2. Mean/Median by month
    rows = list(c.query(Q_MEAN_MEDIAN).result())
    bq_mean = {r.month: float(r.Mean_duration_sec) for r in rows}
    bq_median = {r.month: float(r.Median_duration_sec) for r in rows}
    lines += compare_dict("MEAN DURATION (sec) by month", bq_mean, TARGET_MEAN)
    lines += compare_dict("MEDIAN DURATION (sec) by month", bq_median, TARGET_MEDIAN)

    # 3. Video view schema
    lines.append("--- video_duration_view schema ---")
    try:
        for r in c.query(Q_VIDEO_VIEW_SCHEMA).result():
            lines.append(f"  {r.column_name}\t{r.data_type}")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    # 4. Histogram from video_duration_view
    lines.append("--- HISTOGRAM from video_duration_view vs PowerBI ---")
    try:
        rows = list(c.query(Q_HIST_FROM_VIDEO_VIEW).result())
        bq_hist = {r.bin: float(r.pct) for r in rows}
        for b, tv in TARGET_HIST.items():
            bq_val = bq_hist.get(b, float("nan"))
            delta = bq_val - tv
            flag = "" if abs(delta) < 1e-3 else "  *** MISMATCH"
            lines.append(f"  {b}: bq={bq_val:.10g}  powerbi={tv:.10g}  delta={delta:.6g}{flag}")
    except Exception as e:
        lines.append(f"  ERROR: {e}")

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)
