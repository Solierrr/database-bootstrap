UNWIND $rows AS row
MERGE (unit:LocalUnit {graph_key: $source + '|' + $sync_version + '|' + row.id})
SET unit.id = row.id,
    unit.location_type = row.location_type,
    unit.complement = row.complement,
    unit.geolocation_count = row.geolocation_count,
    unit.latitude = row.latitude,
    unit.longitude = row.longitude,
    unit.source = $source,
    unit.sync_version = $sync_version
