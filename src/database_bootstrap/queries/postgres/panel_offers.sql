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
  AND stock.quantity > 0
  AND (
      offer.expiration_date IS NULL
      OR offer.expiration_date > CURRENT_TIMESTAMP
  )
ORDER BY offer.id
