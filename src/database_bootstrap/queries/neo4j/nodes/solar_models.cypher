UNWIND $rows AS row
MERGE (model:SolarModel {graph_key: $source + '|' + $sync_version + '|' + row.model_id})
SET model.id = row.model_id,
    model.brand = row.brand,
    model.model = row.model,
    model.power_wp = row.power_wp,
    model.efficiency = row.efficiency,
    model.dimension = row.dimension,
    model.weight = row.weight,
    model.status = row.model_status,
    model.source = $source,
    model.sync_version = $sync_version
