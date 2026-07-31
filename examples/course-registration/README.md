# Sample incident: course registration slows at peak

No deploy today, so the tool must resist "it's always the last deploy" thinking and
reason about **load + cold cache + a missing index** interacting.

The cold Redis cache at window-open (30s TTL, 96% miss rate) forces every request to
recompute `seats_remaining` from the DB, where a full table scan on `enrollments`
(no index) pins reg-db CPU at 97%. The index-less query added 6 days ago is a latent
contributing factor exposed only under peak load.

## Files

Inputs:
- `description.txt`
- `logs.txt`
- `deployment-notes.md`
- `alerts.txt`

Example output:
- `example-output.json`
- `example-postmortem.md`

Model output is not deterministic. A fresh live run should follow the same evidence, but
may differ in wording, ordering, and confidence values.
