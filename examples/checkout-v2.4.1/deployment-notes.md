# Recent changes

**Release v2.4.1 (14:05)**
- checkout-svc: raised DB connection pool per pod from 10 -> 20 to reduce p99 latency.
- No schema changes.

**Earlier today, 09:30**
- reporting-svc deployed a new hourly export job that connects directly to orders-db.
- Runs at :00 of each hour.
