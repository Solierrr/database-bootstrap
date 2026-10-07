SELECT
    profession.id::text AS profession_id,
    profession.name AS profession_name,
    COALESCE(profession.requires_registration, true) AS requires_registration,
    profession.accept_emergency_call
FROM profession
WHERE profession.name IS NOT NULL
  AND BTRIM(profession.name) <> ''
ORDER BY profession.id
