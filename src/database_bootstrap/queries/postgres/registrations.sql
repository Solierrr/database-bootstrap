WITH
-- include: fragments/eligible_technician.sql
,
valid_certifications AS (
    SELECT
        fk_technician AS technician_id,
        COUNT(*)::integer AS valid_certification_count,
        ARRAY_AGG(DISTINCT type ORDER BY type) AS certification_names
    FROM certification
    WHERE validity IS NULL
       OR validity >= CURRENT_TIMESTAMP
    GROUP BY fk_technician
)
SELECT
    professional_registration.fk_technician::text AS technician_id,
    professional_registration.fk_profession::text AS profession_id,
    COALESCE(valid_certifications.valid_certification_count, 0) AS valid_certification_count,
    COALESCE(valid_certifications.certification_names, ARRAY[]::text[]) AS certification_names
FROM professional_registration
JOIN eligible_technician
  ON eligible_technician.technician_id = professional_registration.fk_technician
JOIN profession
  ON profession.id = professional_registration.fk_profession
LEFT JOIN valid_certifications
  ON valid_certifications.technician_id = professional_registration.fk_technician
WHERE profession.name IS NOT NULL
  AND BTRIM(profession.name) <> ''
  AND (
      professional_registration.expiration_date IS NULL
      OR professional_registration.expiration_date >= CURRENT_TIMESTAMP
  )
GROUP BY
    professional_registration.fk_technician,
    professional_registration.fk_profession,
    valid_certifications.valid_certification_count,
    valid_certifications.certification_names
ORDER BY technician_id, profession_id
