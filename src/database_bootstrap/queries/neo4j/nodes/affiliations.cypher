UNWIND $rows AS row
MERGE (affiliation:TechnicianAffiliation {graph_key: $source + '|' + $sync_version + '|' + row.affiliation_id})
SET affiliation.id = row.affiliation_id,
    affiliation.affiliation_type = row.affiliation_type,
    affiliation.active = row.active,
    affiliation.company_id = row.company_id,
    affiliation.company_trade_name = row.company_trade_name,
    affiliation.company_geolocation_count = row.company_geolocation_count,
    affiliation.company_latitude = row.company_latitude,
    affiliation.company_longitude = row.company_longitude,
    affiliation.source = $source,
    affiliation.sync_version = $sync_version
