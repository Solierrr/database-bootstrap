eligible_technician AS (
    SELECT technician.id AS technician_id
    FROM technician
    JOIN person
      ON person.id = technician.fk_person
    JOIN users
      ON users.id = person.fk_users
    WHERE users.active IS TRUE
      AND technician.status = 'APPROVED'
)
