-- Replicated logic for Page 3 visuals: Duration of Audio Recordings

-- Visual 1: Audio recording max_duration_hour by month
SELECT
  month,
  MAX(max_duration_sec) / 3600.0 AS max_duration_hour
FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
GROUP BY month
ORDER BY month;

-- Visual 2: Mean_duration_sec and Median_duration_sec by month
WITH x AS (
  SELECT
    month,
    mean_duration_sec,
    median_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
  WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
)
SELECT
  month,
  AVG(mean_duration_sec) AS Mean_duration_sec,
  APPROX_QUANTILES(median_duration_sec, 2)[OFFSET(1)] AS Median_duration_sec
FROM x
GROUP BY month
ORDER BY month;

-- Visual 3: Histogram of Audio Recording Duration (bin(A), Percentage of count)
-- Best-fit replication from chart values:
-- Source table: audio_recording_events_stripped
-- Bin rules by duration_sec
-- Percentage of total count with a cutoff near refresh processing boundary.
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
    COUNT(*) AS count
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  WHERE TIMESTAMP_MICROS(event_timestamp) < TIMESTAMP '2026-05-29 21:00:00+00'
  GROUP BY bin
),
all_count AS (
  SELECT SUM(count) AS total_count FROM base
)
SELECT
  bin,
  count,
  SAFE_DIVIDE(count, total_count) AS pct_of_total
FROM base, all_count
ORDER BY CASE bin
  WHEN '0-1m' THEN 1
  WHEN '1-5m' THEN 2
  WHEN '5-10m' THEN 3
  WHEN '10-15m' THEN 4
  WHEN '15-20m' THEN 5
  WHEN '20-25m' THEN 6
  WHEN '25-30m' THEN 7
  WHEN '0.5-1h' THEN 8
  WHEN '1-8h' THEN 9
  WHEN '8-24h' THEN 10
  WHEN '>24h' THEN 11
  ELSE 99
END;
