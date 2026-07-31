# Sample incident: checkout fails after v2.4.1

A deliberately layered scenario. The obvious story ("the deploy broke checkout")
is only half true and is designed to test whether the tool resists **anchoring**
and **post-hoc** reasoning.

## The trap
`v2.4.1` did change checkout (pool 10 -> 20 per pod). But the *actual* limit hit is
`orders-db max_connections=100`. With 6 pods x 20 = 120 requested, plus 74 idle
connections opened by the unrelated **reporting-svc** export job at 14:00, the shared
database runs out of connections. The checkout deploy is a **contributing factor**,
not the whole root cause — and autoscaling checkout 6 -> 10 pods at 14:15 makes it worse.

A good analysis should surface at least:
- H: checkout pool increase overwhelmed shared DB connection ceiling
- H: reporting-svc hourly job consumed a large share of connections (base-rate / hidden cause)
- H: autoscaling amplified connection demand after the incident began
and should flag that blaming the deploy alone is anchoring.

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
