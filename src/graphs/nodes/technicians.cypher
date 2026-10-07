// dataset: technicians
UNWIND $rows AS row
MERGE (technician:Technician {graph_key: $source + '|' + $sync_version + '|' + row.technician_id})
SET technician.id = row.technician_id,
    technician.name = row.name,
    technician.crea = row.crea,
    technician.user_active = true,
    technician.average_rating_global = row.average_rating_global,
    technician.review_count_global = row.review_count_global,
    technician.assigned_service_count_global = row.assigned_service_count_global,
    technician.completed_service_count_global = row.completed_service_count_global,
    technician.canceled_service_count_global = row.canceled_service_count_global,
    technician.active_workload = row.active_workload,
    technician.source = $source,
    technician.sync_version = $sync_version
RETURN count(*) AS merged
