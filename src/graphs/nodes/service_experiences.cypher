// dataset: service_experiences
UNWIND $rows AS row
MERGE (experience:ServiceExperience {
    graph_key: $source + '|' + $sync_version + '|' + row.technician_id + '|' + row.normalized_purpose
})
SET experience.technician_id = row.technician_id,
    experience.normalized_purpose = row.normalized_purpose,
    experience.completed_count = row.completed_count,
    experience.source = $source,
    experience.sync_version = $sync_version
RETURN count(*) AS merged
