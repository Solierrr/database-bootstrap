MATCH (state:SyncState {
    source: $source,
    lock_token: $sync_version,
    active_version: $sync_version
})
RETURN state.active_version AS active_version,
       state.previous_version AS previous_version,
       coalesce(state.pending_cleanup_versions, []) AS cleanup_versions
