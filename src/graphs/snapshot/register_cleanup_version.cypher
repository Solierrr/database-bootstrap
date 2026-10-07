MATCH (state:SyncState {source: $source, lock_token: $sync_version})
WITH state, coalesce(state.pending_cleanup_versions, []) AS pending
WHERE (state.active_version IS NULL
       OR $cleanup_version <> state.active_version)
  AND (state.previous_version IS NULL
       OR $cleanup_version <> state.previous_version)
SET state.pending_cleanup_versions = CASE
    WHEN $cleanup_version IN pending THEN pending
    ELSE pending + [$cleanup_version]
END
RETURN state.pending_cleanup_versions AS cleanup_versions
