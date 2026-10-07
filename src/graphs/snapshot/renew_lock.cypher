MATCH (state:SyncState {
    source: $source,
    lock_token: $sync_version,
    sync_in_progress: true
})
SET state.lock_expires_at = datetime() + duration({seconds: $lease_seconds})
RETURN state.lock_token AS lock_token
