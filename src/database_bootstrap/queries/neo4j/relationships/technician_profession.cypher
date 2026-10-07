UNWIND $rows AS row
MATCH (technician:Technician {graph_key: $source + '|' + $sync_version + '|' + row.technician_id})
MATCH (profession:Profession {graph_key: $source + '|' + $sync_version + '|' + row.profession_id})
MERGE (technician)-[registration:REGISTERED_AS]->(profession)
SET registration.valid_certification_count = row.valid_certification_count,
    registration.certification_names = row.certification_names,
    registration.source = $source,
    registration.sync_version = $sync_version
