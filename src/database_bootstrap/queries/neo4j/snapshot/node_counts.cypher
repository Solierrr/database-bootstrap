MATCH (node)
WHERE node.source = $source
  AND node.sync_version = $sync_version
RETURN labels(node)[0] AS name, count(node) AS total
