from pathlib import Path

from google.cloud import bigquery

OUTPUT_PATH = Path("tmp_validate_page2_recordings_result.txt")

QUERY = """
WITH audio AS (
  SELECT month, SUM(active_audio_users) AS active_audio_users
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
  GROUP BY month
),
video AS (
  SELECT month, SUM(active_video_users) AS active_video_users
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_video_recordings_aggregated`
  GROUP BY month
),
live AS (
  SELECT month, SUM(active_livestream_users) AS active_livestream_users
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_livestream_recordings_aggregated`
  GROUP BY month
),
combined_from_3_tables AS (
  SELECT
    COALESCE(a.month, v.month, l.month) AS month,
    COALESCE(a.active_audio_users, 0) AS active_audio_users,
    COALESCE(v.active_video_users, 0) AS active_video_users,
    COALESCE(l.active_livestream_users, 0) AS active_livestream_users
  FROM audio a
  FULL OUTER JOIN video v USING (month)
  FULL OUTER JOIN live l USING (month)
),
combined_reference AS (
  SELECT
    month,
    SUM(active_audio_users) AS active_audio_users,
    SUM(active_video_users) AS active_video_users,
    SUM(active_livestream_users) AS active_livestream_users
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_country_active_users_aggregated`
  GROUP BY month
)
SELECT
  c3.month,
  c3.active_audio_users AS audio_from_3_tables,
  cr.active_audio_users AS audio_from_reference,
  c3.active_audio_users - cr.active_audio_users AS audio_delta,
  c3.active_video_users AS video_from_3_tables,
  cr.active_video_users AS video_from_reference,
  c3.active_video_users - cr.active_video_users AS video_delta,
  c3.active_livestream_users AS livestream_from_3_tables,
  cr.active_livestream_users AS livestream_from_reference,
  c3.active_livestream_users - cr.active_livestream_users AS livestream_delta
FROM combined_from_3_tables c3
LEFT JOIN combined_reference cr USING (month)
WHERE CAST(c3.month AS STRING) >= '2025-09'
ORDER BY c3.month
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
    try:
        main()
    except Exception as exc:
        OUTPUT_PATH.write_text(
            f"ERROR\n{type(exc).__name__}\n{exc}\n", encoding="ascii", errors="ignore"
        )
        raise
