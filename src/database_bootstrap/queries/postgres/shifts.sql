WITH
-- include: fragments/eligible_technician.sql
SELECT
    shift.id::text AS shift_id,
    shift.fk_technician::text AS technician_id,
    shift.day_week::text AS day_week,
    shift.start_date AS start_at,
    shift.end_date AS end_at
FROM shift
JOIN eligible_technician
  ON eligible_technician.technician_id = shift.fk_technician
ORDER BY shift.id
