UNWIND $rows AS row
MATCH (affiliation:TechnicianAffiliation {graph_key: $source + '|' + $sync_version + '|' + row.affiliation_id})
MATCH (service:TechnicalService {graph_key: $source + '|' + $sync_version + '|' + row.service_id})
MERGE (affiliation)-[assignment:ASSIGNED_TO {executor_id: row.executor_id}]->(service)
SET assignment.function = row.function,
    assignment.source = $source,
    assignment.sync_version = $sync_version
