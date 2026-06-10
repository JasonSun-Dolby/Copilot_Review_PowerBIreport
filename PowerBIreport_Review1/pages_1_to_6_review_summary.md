# Report Review Summary: Pages 1 to 6

This document summarizes the review work completed for pages 1 through 6 of the Power BI report, based on the query scripts, result files, and datasource notes saved in this workspace.

## Overall Summary

- Pages 1 to 4 have concrete review artifacts in the workspace, including BigQuery validation scripts and saved result outputs.
- Pages 5 and 6 have datasource mapping notes, but there is not the same level of saved page-specific validation output as pages 1 to 4.
- The main pattern across the review was to compare live Power BI values with BigQuery aggregated tables and, where needed, underlying stripped event tables.

## Page 1

Focus of review:

- Active users by month.
- Cross-check of audio, video, livestream, and total active users.

What we did:

- Confirmed the reference table schema and monthly values from `monthly_country_active_users_aggregated`.
- Reviewed the SQL logic used to derive active users from raw events with a duration threshold.
- Spot-checked a country-level example for India in 2026-02.

Key findings:

- The active-user reference table contains the expected columns: `active_audio_users`, `active_video_users`, `active_livestream_users`, and `total_active_users`.
- Monthly totals were captured for 2025-09 through 2026-05.
- Example reference value for India in 2026-02 was: audio 134,177, video 18,408, livestream 11, total 140,823.

Evidence:

- `SQL_activeUser.txt`
- `tmp_query_monthly_active.py`
- `tmp_query_monthly_active_result.txt`
- `tmp_query_india_2026_02.py`
- `tmp_query_india_2026_02_result.txt`

## Page 2

Focus of review:

- Recording totals across audio, video, and livestream.
- Monthly and grand-total checks for track counts and total duration.

What we did:

- Queried monthly totals from `monthly_audio_recordings_aggregated`, `monthly_video_recordings_aggregated`, and `monthly_livestream_recordings_aggregated`.
- Calculated overall totals across all months.
- Pulled a country-level example for India in 2026-02 from the recording aggregate tables.
- Tried to validate active-user-style fields directly from recording tables and confirmed that approach was invalid.

Key findings:

- Monthly recording counts and durations were documented for 2025-11 through 2026-05.
- Overall totals saved during the review were:
  - audio tracks: 33,209,217
  - video tracks: 3,251,038
  - livestream tracks: 7,021
  - audio hours: 1,191,653.776
  - video hours: 77,653.573
  - livestream hours: 1,044.672
- The attempt to query `active_audio_users` from recording aggregate tables failed, which clarified that those fields belong to the active-user reference table rather than the recording tables.

Evidence:

- `tmp_page2_expected_values.py`
- `tmp_page2_expected_values_result.txt`
- `tmp_page2_totals_check.py`
- `tmp_page2_totals_check_result.txt`
- `tmp_page2_expected_india_2026_02.py`
- `tmp_page2_expected_india_2026_02_result.txt`
- `tmp_validate_page2_recordings.py`
- `tmp_validate_page2_recordings_result.txt`

## Page 3

Focus of review:

- Audio recording duration page.
- Validation of max duration, mean duration, median duration, and duration histogram.

What we did:

- Replicated the page logic against `monthly_audio_recordings_aggregated` for max, mean, and median metrics.
- Compared histogram behavior against `audio_recording_events_stripped` using the same duration bins as the report.
- Investigated refresh or cutoff effects for the histogram fit.

Key findings:

- The page's max-duration chart aligns with `monthly_audio_recordings_aggregated` using `MAX(max_duration_sec) / 3600`.
- The mean metric aligns with `AVG(mean_duration_sec)`.
- The median metric aligns with median behavior over `median_duration_sec`, with SQL equivalents tested using percentile logic.
- The histogram best matches `audio_recording_events_stripped` with a cutoff near the report refresh boundary, indicating small timing or ETL effects rather than a logic mismatch.

Evidence:

- `tmp_page3_replicated_logic.py`
- `tmp_page3_replicated_logic.sql`
- `tmp_page3_replicated_logic_result.txt`
- `tmp_check_page3_audio_events.py`
- `tmp_check_page3_audio_events_result.txt`
- `tmp_compare_mean_median_audio.py`
- `tmp_compare_mean_median_audio_result.txt`
- `tmp_compare_mean_median_audio_v2.py`
- `tmp_compare_mean_median_audio_v2_result.txt`
- `tmp_find_exact_hist_logic.py`
- `tmp_find_exact_hist_logic_result.txt`
- `tmp_optimize_hist_cutoff.py`
- `tmp_optimize_hist_cutoff_result.txt`
- `tmp_optimize_hist_cutoff_second.py`
- `tmp_optimize_hist_cutoff_second_result.txt`
- `tmp_optimize_hist_cutoff_both_sources.py`
- `tmp_optimize_hist_cutoff_both_sources_result.txt`

## Page 4

Focus of review:

- Video recording duration page.
- Validation of max duration, mean duration, median duration, and duration histogram.

What we did:

- Tested multiple candidate interpretations of the page metrics.
- Compared weighted and non-weighted mean logic from `monthly_video_recordings_aggregated`.
- Checked histogram candidates from `video_duration_view` and `video_recording_events_stripped`.
- Ran a final pass against the live visual values.

Key findings:

- Final validation showed the page matches `monthly_video_recordings_aggregated` for:
  - max duration in hours
  - mean duration as `AVG(mean_duration_sec)`
  - median duration using percentile-style logic over `median_duration_sec`
- The histogram is a near-match against `video_recording_events_stripped`, with only tiny residual deltas consistent with refresh or cutoff timing.
- An earlier hypothesis that the page used weighted mean or very large duration values was disproved.

Evidence:

- `tmp_page4_video_validation.py`
- `tmp_page4_video_validation_result.txt`
- `tmp_page4_expected_mean_median.py`
- `tmp_page4_expected_mean_median_result.txt`
- `tmp_page4_video_final.py`
- `tmp_page4_video_final_result.txt`
- `tmp_page4_final_pass.py`
- `tmp_page4_final_pass_result.txt`
- `tmp_page4_video_investigation.py`
- `tmp_page4_video_investigation_result.txt`

## Page 5

Focus of review:

- Import and Export Total page.
- Validation of monthly import and export counts for audio and video.

What we did:

- Queried monthly totals from `monthly_audio_imports_aggregated`, `monthly_audio_exports_aggregated`, `monthly_video_imports_aggregated`, and `monthly_video_exports_aggregated`.
- Confirmed all four tables exist in BigQuery under the correct spelling (`aggregated`, not `aggregared` as written in the datasource note).
- Extracted available columns and month-by-month aggregated values for Nov 2025 – May 2026.
- Computed grand totals across all months.

Key findings:

- Audio imports: ~144K–160K per month; grand total 1,057,435 imports across all months.
- Audio exports: ~1.2M–1.34M per month; grand total 8,811,910 exports.
- Video imports: ~100K–110K per month; grand total 728,595 imports.
- Video exports: ~319K–364K per month; grand total 2,350,308 exports.
- Columns available per import table: `num_imports`, `total_track_duration`, `total_import_duration`, `num_batch_imports`.
- Columns available per export table: `num_exports`, `total_duration`, `total_exported_track_duration`, `total_exporting_time`.
- The datasource note spells all tables as `aggregared` but the actual BigQuery table names are `aggregated`.

Evidence:

- `tmp_page5_import_export_total.py`
- `tmp_page5_import_export_total_result.txt`
- `tmp_discover_import_export_tables.py`

## Page 6

Focus of review:

- Recordings / Import / Export Trend page.
- Validation of monthly trends for all six source tables side-by-side.

What we did:

- Queried all six source tables: `monthly_audio_recordings_aggregated`, `monthly_audio_imports_aggregated`, `monthly_audio_exports_aggregated`, `monthly_video_recordings_aggregated`, `monthly_video_imports_aggregated`, `monthly_video_exports_aggregated`.
- Confirmed the recording tables use plural `recordings` (not singular `recording` as in the datasource note).
- Extracted month-by-month values and assembled a side-by-side trend comparison.

Key findings (num_tracks / num_imports / num_exports by month):

| month   | audio_rec | audio_imp | audio_exp | video_rec | video_imp | video_exp |
|---------|----------:|----------:|----------:|----------:|----------:|----------:|
| 2025-11 | 4,710,322 | 144,913   | 1,221,707 | 421,517   | 101,068   | 320,861   |
| 2025-12 | 4,785,624 | 145,771   | 1,256,856 | 435,140   | 102,441   | 319,266   |
| 2026-01 | 4,925,224 | 146,302   | 1,277,111 | 490,216   | 101,232   | 346,076   |
| 2026-02 | 4,552,469 | 150,332   | 1,199,625 | 454,848   | 100,055   | 319,343   |
| 2026-03 | 4,815,902 | 157,453   | 1,279,952 | 494,906   | 109,142   | 347,086   |
| 2026-04 | 4,841,230 | 152,681   | 1,238,133 | 488,135   | 104,861   | 333,700   |
| 2026-05 | 5,079,778 | 159,983   | 1,338,526 | 520,630   | 109,796   | 363,976   |

- Datasource note spellings corrected: `aggregared` → `aggregated`, `recording` → `recordings`.

Evidence:

- `tmp_page6_trend.py`
- `tmp_page6_trend_result.txt`
- `tmp_discover_recording_tables.py`

## Conclusion

- Pages 1 to 6 were reviewed with direct BigQuery checks and saved outputs.
- Page 3 and page 4 duration pages were traced to a combination of monthly aggregated tables for summary metrics and stripped event tables for histogram visuals.
- Pages 5 and 6 were validated against import/export aggregated tables. The datasource note contained two typos: `aggregared` (should be `aggregated`) and `recording` (should be `recordings` for the recording tables).