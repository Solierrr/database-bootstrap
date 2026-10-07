UNWIND $rows AS row
MERGE (offer:SolarOffer {graph_key: $source + '|' + $sync_version + '|' + row.offer_id})
SET offer.id = row.offer_id,
    offer.unit_price_cents = row.unit_price_cents,
    offer.availability = row.availability,
    offer.inventory_quantity = row.inventory_quantity,
    offer.effective_availability = row.effective_availability,
    offer.expiration_at = row.expiration_at,
    offer.accepted_proposal_quantity = row.accepted_proposal_quantity,
    offer.source = $source,
    offer.sync_version = $sync_version
