MATCH (state:SyncState {source: $source, lock_token: $sync_version})
SET state.sync_in_progress = false
REMOVE state.lock_token, state.locked_at, state.lock_expires_at
