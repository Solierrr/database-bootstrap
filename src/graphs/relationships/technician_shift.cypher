// dataset: shifts
UNWIND $rows AS row
MATCH (technician:Technician {graph_key: $source + '|' + $sync_version + '|' + row.technician_id})
MATCH (shift:Shift {graph_key: $source + '|' + $sync_version + '|' + row.shift_id})
MERGE (technician)-[relation:HAS_SHIFT]->(shift)
SET relation.source = $source,
    relation.sync_version = $sync_version
RETURN count(*) AS merged
