WITH
-- include: fragments/address_geolocation.sql
SELECT
    local_unit.id::text AS id,
    local_unit.location_type::text AS location_type,
    local_unit.complement,
    COALESCE(address_geolocation.geolocation_count, 0) AS geolocation_count,
    address_geolocation.latitude,
    address_geolocation.longitude
FROM local_unit
LEFT JOIN address_geolocation
  ON address_geolocation.fk_address = local_unit.fk_address
ORDER BY local_unit.id
