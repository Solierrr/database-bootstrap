MATCH (state:SyncState {source: $source, lock_token: $sync_version})
OPTIONAL MATCH (node)
WHERE node.source = $source
  AND node.sync_version IS NOT NULL
  AND node.sync_version <> $sync_version
  AND (state.active_version IS NULL
       OR node.sync_version <> state.active_version)
  AND (state.previous_version IS NULL
       OR node.sync_version <> state.previous_version)
WITH state,
     coalesce(state.pending_cleanup_versions, []) AS pending,
     collect(DISTINCT node.sync_version) AS unreferenced
SET state.pending_cleanup_versions = pending + [
    version IN unreferenced
    WHERE version IS NOT NULL AND NOT version IN pending
]
RETURN state.pending_cleanup_versions AS cleanup_versions
