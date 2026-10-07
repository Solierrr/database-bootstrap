CREATE INDEX local_unit_lookup IF NOT EXISTS FOR (n:LocalUnit) ON (n.source, n.sync_version, n.id);
CREATE INDEX profession_lookup IF NOT EXISTS FOR (n:Profession) ON (n.source, n.sync_version, n.id);
CREATE INDEX technical_service_lookup IF NOT EXISTS FOR (n:TechnicalService) ON (n.source, n.sync_version, n.id);
CREATE INDEX offer_snapshot_lookup IF NOT EXISTS FOR (n:SolarOffer) ON (n.source, n.sync_version);
CREATE INDEX affiliation_snapshot_lookup IF NOT EXISTS FOR (n:TechnicianAffiliation) ON (n.source, n.sync_version, n.active);
