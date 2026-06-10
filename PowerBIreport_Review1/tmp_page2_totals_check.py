from pathlib import Path

from google.cloud import bigquery

OUTPUT_PATH = Path("tmp_page2_totals_check_result.txt")

QUERY = """
WITH audio AS (
  SELECT
    SUM(num_tracks) AS tracks,
    SUM(total_duration_sec) / 3600.0 AS hours
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
),
video AS (
  SELECT
    SUM(num_tracks) AS tracks,
    SUM(total_duration_sec) / 3600.0 AS hours
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_video_recordings_aggregated`
),
live AS (
  SELECT
    SUM(num_tracks) AS tracks,
    SUM(total_duration_sec) / 3600.0 AS hours
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_livestream_recordings_aggregated`
)
SELECT
  audio.tracks AS audio_tracks,
  video.tracks AS video_tracks,
  live.tracks AS livestream_tracks,
  audio.hours AS audio_hours,
  video.hours AS video_hours,
  live.hours AS livestream_hours
FROM audio, video, live
"""


def main() -> None:
    client = bigquery.Client(project="ap3-prod-0e613121")
    row = list(client.query(QUERY).result())[0]

    lines = [str(dict(row.items()))]
    OUTPUT_PATH.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", OUTPUT_PATH)


if __name__ == "__main__":
    main()
