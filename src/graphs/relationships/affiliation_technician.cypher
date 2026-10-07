// dataset: affiliations
UNWIND $rows AS row
MATCH (affiliation:TechnicianAffiliation {graph_key: $source + '|' + $sync_version + '|' + row.affiliation_id})
MATCH (technician:Technician {graph_key: $source + '|' + $sync_version + '|' + row.technician_id})
MERGE (affiliation)-[relation:OF_TECHNICIAN]->(technician)
SET relation.source = $source,
    relation.sync_version = $sync_version
RETURN count(*) AS merged
