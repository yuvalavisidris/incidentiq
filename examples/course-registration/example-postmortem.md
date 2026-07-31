# Incident: registration slowdown at window open

## Impact
From 20:00, students experienced average page latency above 8 seconds, with reports of the site appearing frozen and failures adding courses. Degradation persisted through at least 20:03. Registration is time-sensitive and contended, so slow responses carry a fairness cost beyond the technical impact.

## Timeline
- **19:58:11** — normal: 180 requests/s at 210ms.
- **20:00:04** — window opens; traffic rises to 2400 requests/s.
- **~20:00:04 (inferred)** — capacity cache is cold; the 30-second TTL means no entries survive from before the window.
- **20:00:22** — average latency 8200ms.
- **20:00:30** — 96% cache miss rate on `course:capacity:*`.
- **20:00:45** — `seats_remaining` query takes 6100ms via a full table scan on `enrollments`.
- **20:01:10** — reg-db CPU at 97%, 400+ slow queries.
- **20:03:00** — traffic 2100/s, latency 9100ms, no recovery.

## Leading hypothesis (not confirmed)
Three conditions combined. The capacity cache was cold at window open because of a 30-second TTL with no pre-warming. Every request therefore fell through to `seats_remaining`, which performs a full table scan on `enrollments`. Under 2400 requests/s this saturated database CPU, which in turn slowed every other query.

No single one of these is sufficient. The system ran normally for six days with the same schema, and the cache handles ordinary traffic without difficulty.

**This has not been verified.** The missing index is inferred from a single log phrase and has not been confirmed against the schema.

## Contributing factors
- A 30-second TTL guarantees a cold cache at any window that opens after a quiet period.
- A query without a supporting index remained harmless under low traffic and dangerous under peak traffic.
- Capacity is recomputed on demand rather than refreshed in the background.

## What we still need to verify
- Which index is missing, confirmed by EXPLAIN.
- Whether Redis was healthy or evicting keys.
- Whether previous windows showed the same pattern.
- Whether any registrations were lost or duplicated during the degradation.

## Follow-up actions
1. EXPLAIN the `seats_remaining` query and add the missing index. *(high)*
2. Pre-warm the capacity cache before the next window. *(high)*
3. Raise the TTL or move to background refresh. *(high)*
4. Review Redis metrics for the incident window. *(medium)*
5. Load-test at peak volume before the next window. *(medium)*

*Blameless: the caching design was reasonable for steady traffic. The gap was that no test exercised a cold cache at peak volume.*
