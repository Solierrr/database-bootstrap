MATCH (state:SyncState {source: $source, lock_token: $sync_version})
WITH state
MATCH (node)
WHERE node.source = $source
  AND node.sync_version IN $cleanup_versions
  AND (state.active_version IS NULL
       OR node.sync_version <> state.active_version)
  AND (state.previous_version IS NULL
       OR node.sync_version <> state.previous_version)
DETACH DELETE node
