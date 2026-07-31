# Incident: checkout failures following v2.4.1

## Impact
Between roughly 14:12 and at least 14:16, POST /api/checkout returned HTTP 500 at a measured 41% error rate against a 2% alerting threshold. Customers could not complete payment. Six support tickets between 14:14 and 14:40 report a card charge without an order confirmation, so financial reconciliation is required regardless of the technical cause.

## Timeline
- **14:05:02** — checkout-svc v2.4.1 deployed, 6 replicas. Connection pool raised from 10 to 20 per pod.
- **14:05:40** — all pods pass health checks. No errors.
- **~14:00 (inferred)** — reporting-svc hourly export job begins its scheduled run.
- **14:11:56** — payment.finalize latency rises to 1900ms against a 240ms baseline.
- **14:12:03** — first timeouts and 500s. Checkout pool exhausted at 20/20.
- **14:12:09** — orders-db reports max_connections=100, active=100.
- **14:12:10** — reporting-svc observed holding 74 idle connections to orders-db.
- **14:15:00** — autoscaler raises checkout 6 to 10 replicas.
- **14:16:41** — errors continue.

## Leading hypothesis (not confirmed)
Combined demand on the shared `orders-db` exceeded its ceiling of 100 connections. After v2.4.1, checkout alone could request up to 120 connections across 6 pods, while reporting-svc held 74 idle connections against the same limit. The failures present as connection timeouts and pool exhaustion rather than application faults, which is consistent with this explanation.

**This has not been verified.** Actual per-service connection counts are not present in the available evidence.

## Contributing factors
- The v2.4.1 pool increase was sized against a single service, not against the shared ceiling of the database.
- A reporting export job deployed the same morning began consuming a large share of that ceiling.
- Autoscaling responded to CPU pressure by adding replicas, which increases connection demand rather than relieving it.

## What we still need to verify
- Real per-service connection counts at the time of the incident.
- Whether earlier hourly export runs also approached the ceiling.
- Whether payments were captured for failed checkouts.
- Why errors began seven minutes after the deploy rather than immediately.

## Follow-up actions
1. Measure connections by `application_name` during a reproduction. *(high)*
2. Pause the reporting export and observe the error rate. *(high)*
3. Reduce the per-pod pool or cap replicas and re-measure. *(high)*
4. Reconcile payment captures against orders for the incident window. *(medium)*
5. Alert on connection utilisation below the hard ceiling. *(low)*

*This is a blameless review. The pool change was a reasonable latency fix; the gap was that no single owner held a view of total connection demand on a shared database.*
