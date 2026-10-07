MERGE (state:SyncState {source: $source})
ON CREATE SET state.sync_in_progress = false,
              state.lock_fence = 0
SET state.lock_fence = coalesce(state.lock_fence, 0) + 1
WITH state
WHERE coalesce(state.sync_in_progress, false) = false
   OR (state.lock_expires_at IS NOT NULL
       AND state.lock_expires_at < datetime())
   OR (state.lock_expires_at IS NULL
       AND (state.locked_at IS NULL
            OR state.locked_at < datetime() - duration('PT15M')))
SET state.sync_in_progress = true,
    state.lock_token = $sync_version,
    state.locked_at = datetime(),
    state.lock_expires_at = datetime() + duration({seconds: $lease_seconds})
RETURN state.active_version AS active_version,
       state.lock_fence AS lock_fence
