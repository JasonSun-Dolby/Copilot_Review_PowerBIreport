"""
Page 6 – 'Recordings/Import/Export_Trend'
Validation script: query monthly values for all six source tables and
compare against Power BI trend visual values.

Source tables:
  monthly_audio_recording_aggregated / aggregared   (singular)
  monthly_audio_imports_aggregated   / aggregared
  monthly_audio_exports_aggregated   / aggregared
  monthly_video_recording_aggregated / aggregared   (singular)
  monthly_video_imports_aggregated   / aggregared
  monthly_video_exports_aggregated   / aggregared

Note: confirmed recording tables use plural 'recordings' in BigQuery,
      so singular 'recording' is also tried.
"""
from pathlib import Path
from google.cloud import bigquery

PROJECT = "ap3-prod-0e613121"
DATASET = "analytics_184529778"
out = Path("tmp_page6_trend_result.txt")

DATE_START = "2025-09-01"
DATE_END = "2026-05-01"



def get_numeric_cols(client, table):
    schema_q = f"""
    SELECT column_name, data_type
    FROM `{PROJECT}.{DATASET}`.INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = '{table}'
    ORDER BY ordinal_position
    """
    return [r.column_name for r in client.query(schema_q).result()
            if r.data_type in ("INT64", "FLOAT64", "NUMERIC", "BIGNUMERIC")
            and r.column_name != "month"]


def query_monthly(client, table, numeric_cols):
    agg_exprs = ", ".join(f"SUM({c}) AS {c}" for c in numeric_cols)
    q = f"""
    SELECT
      FORMAT_DATE('%Y-%m', month) AS month,
      {agg_exprs}
    FROM `{PROJECT}.{DATASET}.{table}`
    WHERE month BETWEEN DATE '{DATE_START}' AND DATE '{DATE_END}'
    GROUP BY 1
    ORDER BY 1
    """
    return list(client.query(q).result())


def main():
    c = bigquery.Client(project=PROJECT)
    lines = []

    table_map = {
        "audio_recording": "monthly_audio_recordings_aggregated",
        "audio_imports":   "monthly_audio_imports_aggregated",
        "audio_exports":   "monthly_audio_exports_aggregated",
        "video_recording": "monthly_video_recordings_aggregated",
        "video_imports":   "monthly_video_imports_aggregated",
        "video_exports":   "monthly_video_exports_aggregated",
    }

    lines.append("=== RESOLVED TABLE NAMES ===")
    for label, tbl in table_map.items():
        lines.append(f"  {label}: {tbl}")

    for label, tbl in table_map.items():
        if tbl is None:
            lines.append(f"\n=== {label.upper()}: TABLE NOT FOUND ===")
            continue

        lines.append(f"\n=== {label.upper()} monthly values ({tbl}) ===")
        try:
            num_cols = get_numeric_cols(c, tbl)
            rows = query_monthly(c, tbl, num_cols)
            lines.append("  Columns: " + ", ".join(num_cols))
            for r in rows:
                vals = {col: r[col] for col in num_cols}
                lines.append(f"  {r.month}: " + "  ".join(
                    f"{col}={vals[col]:,.2f}" if isinstance(vals[col], float)
                    else f"{col}={vals[col]:,}" if vals[col] is not None
                    else f"{col}=None"
                    for col in num_cols
                ))
        except Exception as e:
            lines.append(f"  ERROR: {e}")

    # ── Side-by-side monthly comparison for trend chart ─────────────────────
    lines.append("\n=== SIDE-BY-SIDE: num_tracks by month (for trend visual) ===")
    lines.append(f"  {'month':<10}  {'audio_rec':>12}  {'audio_imp':>12}  "
                 f"{'audio_exp':>12}  {'video_rec':>12}  {'video_imp':>12}  {'video_exp':>12}")

    monthly = {}
    for label, tbl in table_map.items():
        if tbl is None:
            continue
        try:
            num_cols = get_numeric_cols(c, tbl)
            track_col = next((col for col in ("num_tracks", "num_exports", "num_imports",
                                               "total_tracks") if col in num_cols), None)
            if track_col is None:
                # fallback: first numeric col
                track_col = num_cols[0] if num_cols else None
            if track_col is None:
                continue
            q = f"""
            SELECT FORMAT_DATE('%Y-%m', month) AS month, SUM({track_col}) AS val
            FROM `{PROJECT}.{DATASET}.{tbl}`
            WHERE month BETWEEN DATE '{DATE_START}' AND DATE '{DATE_END}'
            GROUP BY 1 ORDER BY 1
            """
            for r in c.query(q).result():
                if r.month not in monthly:
                    monthly[r.month] = {}
                monthly[r.month][label] = r.val
        except Exception as e:
            lines.append(f"  ({label} side-by-side error: {e})")

    order = ["audio_recording", "audio_imports", "audio_exports",
             "video_recording", "video_imports", "video_exports"]
    for month in sorted(monthly.keys()):
        row = monthly[month]
        vals = "  ".join(
            f"{row.get(k, 0):>12,.0f}" for k in order
        )
        lines.append(f"  {month:<10}  {vals}")

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)


if __name__ == "__main__":
    main()
