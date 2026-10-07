UNWIND $rows AS row
MERGE (shift:Shift {graph_key: $source + '|' + $sync_version + '|' + row.shift_id})
SET shift.id = row.shift_id,
    shift.day_week = row.day_week,
    shift.start_at = row.start_at,
    shift.end_at = row.end_at,
    shift.source = $source,
    shift.sync_version = $sync_version
