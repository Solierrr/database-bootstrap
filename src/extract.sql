-- fragment: eligible_technician
eligible_technician AS (
    SELECT technician.id AS technician_id
    FROM technician
    JOIN person
      ON person.id = technician.person_id
    JOIN user_account
      ON user_account.id = person.user_id
    WHERE user_account.is_active IS TRUE
      AND technician.status = 'APPROVED'
)

-- fragment: address_geolocation
address_geolocation AS (
    SELECT
        address_id,
        COUNT(*)::integer AS geolocation_count,
        CASE WHEN COUNT(*) = 1 THEN MIN(latitude)::double precision END AS latitude,
        CASE WHEN COUNT(*) = 1 THEN MIN(longitude)::double precision END AS longitude
    FROM geolocation
    WHERE address_id IS NOT NULL
    GROUP BY address_id
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
  ON address_geolocation.address_id = local_unit.address_id
ORDER BY local_unit.id

-- dataset: panel_offers
WITH active_subscriptions AS (
    SELECT
        supplier_id,
        BOOL_OR(
            status = 'PAID'
            AND (ends_at IS NULL OR ends_at > CURRENT_TIMESTAMP)
        ) AS subscription_active
    FROM subscription
    GROUP BY supplier_id
),
stock AS (
    SELECT supplier_id, model_id, SUM(quantity)::integer AS quantity
    FROM inventory
    GROUP BY supplier_id, model_id
),
accepted_usage AS (
    SELECT
        proposal_item.offer_id,
        COALESCE(SUM(proposal_item.quantity), 0)::integer AS accepted_proposal_quantity
    FROM proposal_item
    JOIN proposal
      ON proposal.id = proposal_item.proposal_id
    WHERE proposal.status = 'ACCEPTED'
    GROUP BY proposal_item.offer_id
),
company_geolocation AS (
    SELECT
        company.id AS company_id,
        COUNT(geolocation.id)::integer AS geolocation_count,
        CASE WHEN COUNT(geolocation.id) = 1
            THEN MIN(geolocation.latitude)::double precision
        END AS latitude,
        CASE WHEN COUNT(geolocation.id) = 1
            THEN MIN(geolocation.longitude)::double precision
        END AS longitude
    FROM company
    LEFT JOIN geolocation
      ON geolocation.address_id = company.address_id
    GROUP BY company.id
)
SELECT
    model.id::text AS model_id,
    brand.name AS brand,
    model.model_name AS model,
    model.power_wp::double precision AS power_wp,
    model.efficiency::double precision AS efficiency,
    (model.width * model.length)::double precision AS dimension,
    model.weight::double precision AS weight,
    model.status::text AS model_status,
    offer.id::text AS offer_id,
    ROUND(offer.unit_price * 100)::bigint AS unit_price_cents,
    offer.availability,
    offer.expires_at AS expiration_at,
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
  ON model.id = offer.model_id
JOIN brand
  ON brand.id = model.brand_id
JOIN supplier
  ON supplier.id = offer.supplier_id
JOIN company
  ON company.id = supplier.company_id
JOIN stock
  ON stock.supplier_id = offer.supplier_id
 AND stock.model_id = offer.model_id
JOIN active_subscriptions
  ON active_subscriptions.supplier_id = supplier.id
 AND active_subscriptions.subscription_active IS TRUE
LEFT JOIN accepted_usage
  ON accepted_usage.offer_id = offer.id
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
      offer.expires_at IS NULL
      OR offer.expires_at > CURRENT_TIMESTAMP
  )
ORDER BY offer.id

-- dataset: professions
SELECT
    profession.id::text AS profession_id,
    profession.name AS profession_name,
    COALESCE(profession.is_registration_required, true) AS requires_registration,
    profession.is_emergency_call_accepted AS accept_emergency_call
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
        technician_id AS technician_id,
        AVG(rating)::double precision AS average_rating,
        COUNT(*)::integer AS review_count
    FROM professional_review
    WHERE is_active IS TRUE
    GROUP BY technician_id
),
service_metrics AS (
    SELECT
        technician_affiliation.technician_id AS technician_id,
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
      ON service_executor.technician_affiliation_id = technician_affiliation.id
    JOIN technical_service
      ON technical_service.id = service_executor.technical_service_id
    GROUP BY technician_affiliation.technician_id
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
        technician_id AS technician_id,
        COUNT(*)::integer AS valid_certification_count,
        ARRAY_AGG(DISTINCT type ORDER BY type) AS certification_names
    FROM certification
    WHERE valid_until_at IS NULL
       OR valid_until_at >= CURRENT_TIMESTAMP
    GROUP BY technician_id
)
SELECT
    professional_registration.technician_id::text AS technician_id,
    professional_registration.profession_id::text AS profession_id,
    COALESCE(valid_certifications.valid_certification_count, 0) AS valid_certification_count,
    COALESCE(valid_certifications.certification_names, ARRAY[]::text[]) AS certification_names
FROM professional_registration
JOIN eligible_technician
  ON eligible_technician.technician_id = professional_registration.technician_id
JOIN profession
  ON profession.id = professional_registration.profession_id
LEFT JOIN valid_certifications
  ON valid_certifications.technician_id = professional_registration.technician_id
WHERE profession.name IS NOT NULL
  AND BTRIM(profession.name) <> ''
  AND (
      professional_registration.expires_at IS NULL
      OR professional_registration.expires_at >= CURRENT_TIMESTAMP
  )
GROUP BY
    professional_registration.technician_id,
    professional_registration.profession_id,
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
    technician_affiliation.is_active AS active,
    technician_affiliation.technician_id::text AS technician_id,
    company.id::text AS company_id,
    company.trade_name AS company_trade_name,
    COALESCE(address_geolocation.geolocation_count, 0) AS company_geolocation_count,
    address_geolocation.latitude AS company_latitude,
    address_geolocation.longitude AS company_longitude
FROM technician_affiliation
JOIN eligible_technician
  ON eligible_technician.technician_id = technician_affiliation.technician_id
JOIN company
  ON company.id = technician_affiliation.company_id
LEFT JOIN address_geolocation
  ON address_geolocation.address_id = company.address_id
ORDER BY technician_affiliation.id

-- dataset: shifts
WITH
-- include: eligible_technician
SELECT
    shift.id::text AS shift_id,
    shift.technician_id::text AS technician_id,
    shift.day_week::text AS day_week,
    shift.starts_at AS start_at,
    shift.ends_at AS end_at
FROM shift
JOIN eligible_technician
  ON eligible_technician.technician_id = shift.technician_id
ORDER BY shift.id

-- dataset: technical_services
WITH
-- include: address_geolocation
SELECT
    technical_service.id::text AS service_id,
    technical_service.purpose,
    LOWER(BTRIM(technical_service.purpose)) AS normalized_purpose,
    technical_service.status::text AS status,
    COALESCE(technical_service.scheduled_at, technical_service.created_at) AS scheduled_at,
    technical_service.created_at,
    technical_service.ends_at AS end_at,
    technical_project.id::text AS project_id,
    local_unit.id::text AS local_unit_id,
    COALESCE(address_geolocation.geolocation_count, 0) AS geolocation_count,
    address_geolocation.latitude,
    address_geolocation.longitude
FROM technical_service
JOIN technical_project
  ON technical_project.id = technical_service.technical_project_id
LEFT JOIN local_unit
  ON local_unit.id = technical_project.local_unit_id
LEFT JOIN address_geolocation
  ON address_geolocation.address_id = local_unit.address_id
ORDER BY technical_service.id

-- dataset: service_experiences
WITH
-- include: eligible_technician
SELECT
    technician_affiliation.technician_id::text AS technician_id,
    LOWER(BTRIM(technical_service.purpose)) AS normalized_purpose,
    COUNT(DISTINCT technical_service.id)::integer AS completed_count
FROM technical_service
JOIN service_executor
  ON service_executor.technical_service_id = technical_service.id
JOIN technician_affiliation
  ON technician_affiliation.id = service_executor.technician_affiliation_id
JOIN eligible_technician
  ON eligible_technician.technician_id = technician_affiliation.technician_id
WHERE technical_service.status = 'COMPLETED'
  AND BTRIM(technical_service.purpose) <> ''
GROUP BY
    technician_affiliation.technician_id,
    LOWER(BTRIM(technical_service.purpose))
ORDER BY technician_id, normalized_purpose

-- dataset: assignments
WITH
-- include: eligible_technician
SELECT
    service_executor.id::text AS executor_id,
    service_executor.technical_service_id::text AS service_id,
    service_executor.technician_affiliation_id::text AS affiliation_id,
    service_executor.function AS function
FROM service_executor
JOIN technician_affiliation
  ON technician_affiliation.id = service_executor.technician_affiliation_id
JOIN eligible_technician
  ON eligible_technician.technician_id = technician_affiliation.technician_id
ORDER BY service_executor.id
