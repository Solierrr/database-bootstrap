UNWIND $rows AS row
MATCH (technician:Technician {graph_key: $source + '|' + $sync_version + '|' + row.technician_id})
MATCH (experience:ServiceExperience {
    graph_key: $source + '|' + $sync_version + '|' + row.technician_id + '|' + row.normalized_purpose
})
MERGE (technician)-[relation:HAS_EXPERIENCE]->(experience)
SET relation.source = $source,
    relation.sync_version = $sync_version
