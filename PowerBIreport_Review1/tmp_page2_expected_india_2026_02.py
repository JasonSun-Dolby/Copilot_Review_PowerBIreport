from pathlib import Path

from google.cloud import bigquery

OUTPUT_PATH = Path("tmp_page2_expected_india_2026_02_result.txt")

QUERY = """
SELECT 'audio' AS source, country, month, num_tracks, total_duration_sec
FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
WHERE month = DATE '2026-02-01' AND country = 'India'
UNION ALL
SELECT 'video' AS source, country, month, num_tracks, total_duration_sec
FROM `ap3-prod-0e613121.analytics_184529778.monthly_video_recordings_aggregated`
WHERE month = DATE '2026-02-01' AND country = 'India'
UNION ALL
SELECT 'livestream' AS source, country, month, num_tracks, total_duration_sec
FROM `ap3-prod-0e613121.analytics_184529778.monthly_livestream_recordings_aggregated`
WHERE month = DATE '2026-02-01' AND country = 'India'
ORDER BY source
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
