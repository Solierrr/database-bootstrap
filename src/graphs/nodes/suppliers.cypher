// dataset: panel_offers
UNWIND $rows AS row
MERGE (supplier:Supplier {graph_key: $source + '|' + $sync_version + '|' + row.supplier_id})
SET supplier.id = row.supplier_id,
    supplier.status = row.supplier_status,
    supplier.business_type = row.business_type,
    supplier.company_id = row.company_id,
    supplier.trade_name = row.trade_name,
    supplier.subscription_active = row.subscription_active,
    supplier.geolocation_count = row.supplier_geolocation_count,
    supplier.latitude = row.supplier_latitude,
    supplier.longitude = row.supplier_longitude,
    supplier.source = $source,
    supplier.sync_version = $sync_version
RETURN count(*) AS merged
