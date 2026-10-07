-- fragment: eligible_technician
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

-- fragment: address_geolocation
address_geolocation AS (
    SELECT
        fk_address,
        COUNT(*)::integer AS geolocation_count,
        CASE WHEN COUNT(*) = 1 THEN MIN(latitude)::double precision END AS latitude,
        CASE WHEN COUNT(*) = 1 THEN MIN(longitude)::double precision END AS longitude
    FROM geolocalization
    WHERE fk_address IS NOT NULL
    GROUP BY fk_address
)

-- dataset: local_units
WITH
-- include: address_geolocation
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

-- dataset: panel_offers
WITH active_subscriptions AS (
    SELECT
        fk_supplier,
        BOOL_OR(
            status = 'PAID'
            AND (end_date IS NULL OR end_date > CURRENT_TIMESTAMP)
        ) AS subscription_active
    FROM subscription
    GROUP BY fk_supplier
),
stock AS (
    SELECT fk_supplier, fk_model, SUM(quantity)::integer AS quantity
    FROM inventory
    GROUP BY fk_supplier, fk_model
),
accepted_usage AS (
    SELECT
        proposal_item.fk_offer,
        COALESCE(SUM(proposal_item.quantity), 0)::integer AS accepted_proposal_quantity
    FROM proposal_item
    JOIN proposal
      ON proposal.id = proposal_item.fk_proposal
    WHERE proposal.status = 'ACCEPTED'
    GROUP BY proposal_item.fk_offer
),
company_geolocation AS (
    SELECT
        company.id AS company_id,
        COUNT(geolocalization.id)::integer AS geolocation_count,
        CASE WHEN COUNT(geolocalization.id) = 1
            THEN MIN(geolocalization.latitude)::double precision
        END AS latitude,
        CASE WHEN COUNT(geolocalization.id) = 1
            THEN MIN(geolocalization.longitude)::double precision
        END AS longitude
    FROM company
    LEFT JOIN geolocalization
      ON geolocalization.fk_address = company.fk_address
    GROUP BY company.id
)
SELECT
    model.id::text AS model_id,
    model.brand,
    model.model AS model,
    model.power_wp::double precision AS power_wp,
    model.efficiency::double precision AS efficiency,
    (model.width * model.length)::double precision AS dimension,
    model.weight::double precision AS weight,
    model.status::text AS model_status,
    offer.id::text AS offer_id,
    ROUND(offer.unit_price * 100)::bigint AS unit_price_cents,
    offer.availability,
    offer.expiration_date AS expiration_at,
    stock.quantity AS inventory_quantity,
    LEAST(offer.availability, stock.quantity)::integer AS effective_availability,
    supplier.id::text AS supplier_id,
    supplier.status::text AS supplier_status,
    supplier.business_type,
    company.id::text AS company_id,
    company.trade_name,
    active_subscriptions.subscription_active,
    COALESCE(accepted_usage.accepted_proposal_quantity, 0) AS accepted_proposal_quantity,
    COALESCE(company_geolocation.geolocation_count, 0) AS supplier_geolocation_count,
    company_geolocation.latitude AS supplier_latitude,
    company_geolocation.longitude AS supplier_longitude
FROM offer
JOIN model
  ON model.id = offer.fk_model
JOIN supplier
  ON supplier.id = offer.fk_supplier
JOIN company
  ON company.id = supplier.fk_company
JOIN stock
  ON stock.fk_supplier = offer.fk_supplier
 AND stock.fk_model = offer.fk_model
JOIN active_subscriptions
  ON active_subscriptions.fk_supplier = supplier.id
 AND active_subscriptions.subscription_active IS TRUE
LEFT JOIN accepted_usage
  ON accepted_usage.fk_offer = offer.id
LEFT JOIN company_geolocation
  ON company_geolocation.company_id = company.id
WHERE model.status = 'APPROVED'
  AND model.power_wp > 0
  AND model.efficiency >= 0
  AND model.efficiency <= 100
  AND model.width > 0
  AND model.length > 0
  AND model.weight > 0
  AND supplier.status = 'ACTIVE'
  AND offer.unit_price > 0
  AND offer.availability > 0
  AND 'NaN'::numeric NOT IN (
      model.power_wp, model.efficiency, model.width, model.length, model.weight, offer.unit_price
  )
  AND stock.quantity > 0
  AND (
      offer.expiration_date IS NULL
      OR offer.expiration_date > CURRENT_TIMESTAMP
  )
ORDER BY offer.id

-- dataset: professions
SELECT
    profession.id::text AS profession_id,
    profession.name AS profession_name,
    COALESCE(profession.requires_registration, true) AS requires_registration,
    profession.accept_emergency_call
FROM profession
WHERE profession.name IS NOT NULL
  AND BTRIM(profession.name) <> ''
ORDER BY profession.id

-- dataset: technicians
WITH
-- include: eligible_technician
,
review_scores AS (
    SELECT
        fk_professional AS technician_id,
        AVG(rating)::double precision AS average_rating,
        COUNT(*)::integer AS review_count
    FROM professional_review
    WHERE active IS TRUE
    GROUP BY fk_professional
),
service_metrics AS (
    SELECT
        technician_affiliation.fk_technician AS technician_id,
        COUNT(DISTINCT technical_service.id)::integer AS assigned_service_count,
        COUNT(DISTINCT technical_service.id) FILTER (
            WHERE technical_service.status = 'COMPLETED'
        )::integer AS completed_service_count,
        COUNT(DISTINCT technical_service.id) FILTER (
            WHERE technical_service.status = 'CANCELED'
        )::integer AS canceled_service_count,
        COUNT(DISTINCT technical_service.id) FILTER (
            WHERE technical_service.status IN ('OPEN', 'IN_PROGRESS')
        )::integer AS active_workload
    FROM technician_affiliation
    JOIN service_executor
      ON service_executor.fk_technician_affiliation = technician_affiliation.id
    JOIN technical_service
      ON technical_service.id = service_executor.fk_service
    GROUP BY technician_affiliation.fk_technician
)
SELECT
    technician.id::text AS technician_id,
    'Profissional ' || LEFT(technician.id::text, 8) AS name,
    technician.crea,
    COALESCE(review_scores.average_rating, 0.0) AS average_rating_global,
    COALESCE(review_scores.review_count, 0) AS review_count_global,
    COALESCE(service_metrics.assigned_service_count, 0) AS assigned_service_count_global,
    COALESCE(service_metrics.completed_service_count, 0) AS completed_service_count_global,
    COALESCE(service_metrics.canceled_service_count, 0) AS canceled_service_count_global,
    COALESCE(service_metrics.active_workload, 0) AS active_workload
FROM technician
JOIN eligible_technician
  ON eligible_technician.technician_id = technician.id
LEFT JOIN review_scores
  ON review_scores.technician_id = technician.id
LEFT JOIN service_metrics
  ON service_metrics.technician_id = technician.id
ORDER BY technician.id

-- dataset: registrations
WITH
-- include: eligible_technician
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

-- dataset: affiliations
WITH
-- include: eligible_technician
,
-- include: address_geolocation
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

-- dataset: shifts
WITH
-- include: eligible_technician
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

-- dataset: technical_services
WITH
-- include: address_geolocation
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

-- dataset: service_experiences
WITH
-- include: eligible_technician
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

-- dataset: assignments
WITH
-- include: eligible_technician
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
