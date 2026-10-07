MATCH (state:SyncState {source: $source, lock_token: $sync_version})
SET state.pending_cleanup_versions = [
    version IN coalesce(state.pending_cleanup_versions, [])
    WHERE NOT version IN $cleanup_versions
]
