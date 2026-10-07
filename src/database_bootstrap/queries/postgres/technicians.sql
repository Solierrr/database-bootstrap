WITH
-- include: fragments/eligible_technician.sql
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
