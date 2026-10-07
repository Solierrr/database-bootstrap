WITH
-- include: fragments/eligible_technician.sql
SELECT
    service_executor.id::text AS executor_id,
    service_executor.fk_service::text AS service_id,
    service_executor.fk_technician_affiliation::text AS affiliation_id,
    service_executor.function AS function
FROM service_executor
JOIN technician_affiliation
  ON technician_affiliation.id = service_executor.fk_technician_affiliation
JOIN eligible_technician
  ON eligible_technician.technician_id = technician_affiliation.fk_technician
ORDER BY service_executor.id
