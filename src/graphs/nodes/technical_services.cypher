// dataset: technical_services
UNWIND $rows AS row
MERGE (service:TechnicalService {graph_key: $source + '|' + $sync_version + '|' + row.service_id})
SET service.id = row.service_id,
    service.purpose = row.purpose,
    service.normalized_purpose = row.normalized_purpose,
    service.status = row.status,
    service.scheduled_at = row.scheduled_at,
    service.created_at = row.created_at,
    service.end_at = row.end_at,
    service.project_id = row.project_id,
    service.local_unit_id = row.local_unit_id,
    service.geolocation_count = row.geolocation_count,
    service.latitude = row.latitude,
    service.longitude = row.longitude,
    service.source = $source,
    service.sync_version = $sync_version
RETURN count(*) AS merged
