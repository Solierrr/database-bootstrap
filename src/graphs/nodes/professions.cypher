// dataset: professions
UNWIND $rows AS row
MERGE (profession:Profession {graph_key: $source + '|' + $sync_version + '|' + row.profession_id})
SET profession.id = row.profession_id,
    profession.name = row.profession_name,
    profession.requires_registration = row.requires_registration,
    profession.accept_emergency_call = row.accept_emergency_call,
    profession.source = $source,
    profession.sync_version = $sync_version
RETURN count(*) AS merged
