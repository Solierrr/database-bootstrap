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
