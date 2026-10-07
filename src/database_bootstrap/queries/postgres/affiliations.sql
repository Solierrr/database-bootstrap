WITH
-- include: fragments/eligible_technician.sql
,
-- include: fragments/address_geolocation.sql
SELECT
    technician_affiliation.id::text AS affiliation_id,
    technician_affiliation.affiliation_type::text AS affiliation_type,
    technician_affiliation.active,
    technician_affiliation.fk_technician::text AS technician_id,
    company.id::text AS company_id,
    company.trade_name AS company_trade_name,
    COALESCE(address_geolocation.geolocation_count, 0) AS company_geolocation_count,
    address_geolocation.latitude AS company_latitude,
    address_geolocation.longitude AS company_longitude
FROM technician_affiliation
JOIN eligible_technician
  ON eligible_technician.technician_id = technician_affiliation.fk_technician
JOIN company
  ON company.id = technician_affiliation.fk_company
LEFT JOIN address_geolocation
  ON address_geolocation.fk_address = company.fk_address
ORDER BY technician_affiliation.id
