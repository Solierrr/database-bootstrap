UNWIND $rows AS row
MATCH (offer:SolarOffer {graph_key: $source + '|' + $sync_version + '|' + row.offer_id})
MATCH (model:SolarModel {graph_key: $source + '|' + $sync_version + '|' + row.model_id})
MERGE (offer)-[relation:OF_MODEL]->(model)
SET relation.source = $source,
    relation.sync_version = $sync_version
