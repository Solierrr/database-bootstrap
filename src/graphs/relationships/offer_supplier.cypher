// dataset: panel_offers
UNWIND $rows AS row
MATCH (offer:SolarOffer {graph_key: $source + '|' + $sync_version + '|' + row.offer_id})
MATCH (supplier:Supplier {graph_key: $source + '|' + $sync_version + '|' + row.supplier_id})
MERGE (offer)-[relation:FROM_SUPPLIER]->(supplier)
SET relation.source = $source,
    relation.sync_version = $sync_version
RETURN count(*) AS merged
