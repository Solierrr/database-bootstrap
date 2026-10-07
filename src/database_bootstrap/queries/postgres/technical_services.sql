WITH
-- include: fragments/address_geolocation.sql
SELECT
    technical_service.id::text AS service_id,
    technical_service.purpose,
    LOWER(BTRIM(technical_service.purpose)) AS normalized_purpose,
    technical_service.status::text AS status,
    COALESCE(technical_service.scheduled_date, technical_service.created_at) AS scheduled_at,
    technical_service.created_at,
    technical_service.end_date AS end_at,
    technical_project.id::text AS project_id,
    local_unit.id::text AS local_unit_id,
    COALESCE(address_geolocation.geolocation_count, 0) AS geolocation_count,
    address_geolocation.latitude,
    address_geolocation.longitude
FROM technical_service
JOIN technical_project
  ON technical_project.id = technical_service.fk_technical_project
LEFT JOIN local_unit
  ON local_unit.id = technical_project.fk_local_unit
LEFT JOIN address_geolocation
  ON address_geolocation.fk_address = local_unit.fk_address
ORDER BY technical_service.id
