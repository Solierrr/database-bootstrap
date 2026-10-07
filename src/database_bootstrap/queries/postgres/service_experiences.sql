WITH
-- include: fragments/eligible_technician.sql
SELECT
    technician_affiliation.fk_technician::text AS technician_id,
    LOWER(BTRIM(technical_service.purpose)) AS normalized_purpose,
    COUNT(DISTINCT technical_service.id)::integer AS completed_count
FROM technical_service
JOIN service_executor
  ON service_executor.fk_service = technical_service.id
JOIN technician_affiliation
  ON technician_affiliation.id = service_executor.fk_technician_affiliation
JOIN eligible_technician
  ON eligible_technician.technician_id = technician_affiliation.fk_technician
WHERE technical_service.status = 'COMPLETED'
  AND BTRIM(technical_service.purpose) <> ''
GROUP BY
    technician_affiliation.fk_technician,
    LOWER(BTRIM(technical_service.purpose))
ORDER BY technician_id, normalized_purpose
