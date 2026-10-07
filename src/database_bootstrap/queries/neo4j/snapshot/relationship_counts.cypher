MATCH (start)-[relationship]->(end)
WHERE start.source = $source
  AND start.sync_version = $sync_version
  AND end.source = $source
  AND end.sync_version = $sync_version
RETURN type(relationship) AS name, count(relationship) AS total
