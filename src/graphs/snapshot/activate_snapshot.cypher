MATCH (state:SyncState {source: $source, lock_token: $sync_version})
WITH state,
     state.previous_version AS cleanup_version,
     coalesce(state.pending_cleanup_versions, []) AS pending
SET state.previous_version = state.active_version,
    state.active_version = $sync_version,
    state.activated_at = datetime(),
    state.pending_cleanup_versions = CASE
        WHEN cleanup_version IS NULL OR cleanup_version IN pending
            THEN pending
        ELSE pending + [cleanup_version]
    END
RETURN state.active_version AS active_version,
       state.previous_version AS previous_version,
       state.pending_cleanup_versions AS cleanup_versions
