from pathlib import Path

from google.cloud import bigquery

OUTPUT_PATH = Path("tmp_page2_expected_values_result.txt")

QUERY = """
WITH audio AS (
  SELECT
    month,
    SUM(num_tracks) AS audio_tracks,
    SUM(total_duration_sec) AS audio_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
  GROUP BY month
),
video AS (
  SELECT
    month,
    SUM(num_tracks) AS video_tracks,
    SUM(total_duration_sec) AS video_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_video_recordings_aggregated`
  GROUP BY month
),
live AS (
  SELECT
    month,
    SUM(num_tracks) AS livestream_tracks,
    SUM(total_duration_sec) AS livestream_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_livestream_recordings_aggregated`
  GROUP BY month
)
SELECT
  COALESCE(a.month, v.month, l.month) AS month,
  COALESCE(a.audio_tracks, 0) AS audio_tracks,
  COALESCE(v.video_tracks, 0) AS video_tracks,
  COALESCE(l.livestream_tracks, 0) AS livestream_tracks,
  COALESCE(a.audio_duration_sec, 0) AS audio_duration_sec,
  COALESCE(v.video_duration_sec, 0) AS video_duration_sec,
  COALESCE(l.livestream_duration_sec, 0) AS livestream_duration_sec
FROM audio a
FULL OUTER JOIN video v USING (month)
FULL OUTER JOIN live l USING (month)
WHERE CAST(COALESCE(a.month, v.month, l.month) AS STRING) >= '2025-09'
ORDER BY month
"""


def main() -> None:
    client = bigquery.Client(project="ap3-prod-0e613121")
    rows = list(client.query(QUERY).result())
    lines = ["rows\t" + str(len(rows))]
    for row in rows:
        lines.append(str(dict(row.items())))
    OUTPUT_PATH.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", OUTPUT_PATH)


if __name__ == "__main__":
    main()
