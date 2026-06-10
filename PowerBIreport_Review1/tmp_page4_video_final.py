from pathlib import Path
from datetime import datetime, timezone

from google.cloud import bigquery

out = Path("tmp_page4_video_final_result.txt")

PROJECT = "ap3-prod-0e613121"
DATASET = "analytics_184529778"

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
BIN_ORDER = list(TARGET_HIST.keys())

# 1. Weighted mean/median from aggregated (total_duration_sec / num_tracks)
Q_WEIGHTED = f"""
WITH x AS (
  SELECT
    month,
    mean_duration_sec,
    median_duration_sec,
    num_tracks,
    total_duration_sec,
    PERCENTILE_CONT(median_duration_sec, 0.5) OVER (PARTITION BY month) AS p50
  FROM `{PROJECT}.{DATASET}.monthly_video_recordings_aggregated`
  WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
)
SELECT
  FORMAT_DATE('%Y-%m', month) AS month,
  SUM(total_duration_sec) / SUM(num_tracks) AS weighted_mean_sec,
  ANY_VALUE(p50) AS percentile_cont_median_sec,
  AVG(mean_duration_sec) AS avg_mean_sec
FROM x
GROUP BY 1
ORDER BY 1
"""

# 2. Histogram from video_recording_events_stripped (hourly bins then sweep)
Q_STRIPPED_HOURLY = f"""
WITH b AS (
  SELECT
    TIMESTAMP_TRUNC(TIMESTAMP_MICROS(event_timestamp), HOUR) AS hr,
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
  FROM `{PROJECT}.{DATASET}.video_recording_events_stripped`
  GROUP BY hr, bin
)
SELECT hr, bin, cnt FROM b ORDER BY hr, bin
"""


def sse_score(counts, target):
    total = sum(counts.values())
    sse, max_abs = 0.0, 0.0
    for b in BIN_ORDER:
        pct = counts.get(b, 0) / total if total else 0
        d = pct - target[b]
        sse += d * d
        if abs(d) > max_abs:
            max_abs = abs(d)
    return sse, max_abs


def main():
    c = bigquery.Client(project=PROJECT)
    lines = []

    # 1. Weighted mean/median
    lines.append("===WEIGHTED MEAN/MEDIAN vs PowerBI===")
    for r in c.query(Q_WEIGHTED).result():
        m = r.month
        wm = float(r.weighted_mean_sec)
        p50 = float(r.percentile_cont_median_sec)
        d_mean = wm - TARGET_MEAN.get(m, 0)
        d_med = p50 - TARGET_MEDIAN.get(m, 0)
        flag_m = "" if abs(d_mean) < 0.1 else "  *** MISMATCH"
        flag_med = "" if abs(d_med) < 0.1 else "  *** MISMATCH"
        lines.append(
            f"  {m}: weighted_mean={wm:.6g} target={TARGET_MEAN.get(m):.6g} delta={d_mean:.4g}{flag_m}"
        )
        lines.append(
            f"  {m}: p50_median={p50:.6g} target={TARGET_MEDIAN.get(m):.6g} delta={d_med:.4g}{flag_med}"
        )

    # 2. Best-fit histogram from video_recording_events_stripped
    lines.append("===BEST-FIT HISTOGRAM from video_recording_events_stripped===")
    rows = list(c.query(Q_STRIPPED_HOURLY).result())
    by_hr = {}
    for r in rows:
        hr = r.hr.replace(tzinfo=timezone.utc)
        by_hr.setdefault(hr, {})[r.bin] = int(r.cnt)

    cumulative = {b: 0 for b in BIN_ORDER}
    best = None
    for hr in sorted(by_hr.keys()):
        for b, v in by_hr[hr].items():
            cumulative[b] += v
        sse, max_abs = sse_score(cumulative, TARGET_HIST)
        if best is None or sse < best[0]:
            best = (sse, max_abs, hr, dict(cumulative))

    total = sum(best[3].values())
    lines.append(f"  best_sse={best[0]}  max_abs_diff={best[1]}  best_hour={best[2].isoformat()}")
    for b in BIN_ORDER:
        pct = best[3][b] / total
        lines.append(f"  {b}: bq={pct:.10g}  powerbi={TARGET_HIST[b]:.10g}  delta={pct-TARGET_HIST[b]:.6g}")

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)


if __name__ == "__main__":
    main()
