MATCH (node)
WHERE node.source = $source
  AND node.sync_version IN [$sync_version, $active_version]
WITH labels(node)[0] AS name, node.sync_version AS version, count(node) AS total
WITH name,
     sum(CASE WHEN version = $sync_version THEN total ELSE 0 END) AS staged,
     sum(CASE WHEN version = $active_version THEN total ELSE 0 END) AS active
WHERE active > 0
  AND toFloat(staged) / active < $minimum_ratio
RETURN name, staged, active
UNION
MATCH ()-[relationship]->()
WHERE relationship.source = $source
  AND relationship.sync_version IN [$sync_version, $active_version]
WITH type(relationship) AS name, relationship.sync_version AS version, count(relationship) AS total
WITH name,
     sum(CASE WHEN version = $sync_version THEN total ELSE 0 END) AS staged,
     sum(CASE WHEN version = $active_version THEN total ELSE 0 END) AS active
WHERE active > 0
  AND toFloat(staged) / active < $minimum_ratio
RETURN name, staged, active
