# PiIot / IoT — Critical GitHub Review

Review date: 2026-11-19
Repository: luminerdy/IoT (public)
Published main reviewed: bab023cedeed334ae51eeda698db727938561fcf
Open draft PR: #8, head f390e0b8aa5f1cc176e0e1596f56f5aadec0d6f1
Review type: read-only source/settings review plus isolated tests/probes.
Publication prepared: 2026-11-20. Findings/settings/results below are dated
2026-11-19, not claims of fresh live deployment verification.
Implementation plan: [critical-review-implementation-plan.md](critical-review-implementation-plan.md).

## Executive assessment

The system has meaningful engineering strengths: lossless SQLite migrations,
real isolated-broker ACL tests, signed OTA with anti-rollback, firmware native
logic tests, controlled bench releases, authenticated mutations, and explicit
operational decisions. It is more disciplined than a typical prototype.

It is not yet a reproducible, tightly controlled release system. Highest
priorities are watchdog recovery eligibility, collector trust boundaries,
malformed timestamp resilience, atomic OTA publication, and reconciling the
published repository with the locally developed system. A passing coverage
percentage does not establish these properties.

No arbitrary-image OTA authenticity bypass, SQL injection, or dashboard
mutation-authentication bypass was demonstrated. This is not a declaration
that the system is vulnerability-free or that every path was exhaustively
examined. No live compromise or production outage was established.

## Scope, versions and execution

Published main and local working tree are different review targets. Main is
at an August 30 commit. Draft PR #8 contains 11 commits absent from main,
including telemetry-freshness, diagnostic counters, monitoring, weather and
provisioning work. The local working tree also has uncommitted dashboard/
uptime changes and untracked Phase-1 traceability files. Main and PR diverge;
main is not simply a newer version of the local code.

Verified during this review:
- Published main: full Python suite 127 passed; configured coverage 86.76%.
- Published main: Ruff lint passed; 30 files passed formatting checks.
- Published main identifier scan: 29 accepted fingerprints, zero unexpected,
  two stale baseline entries, using explicit files from git ls-tree. The normal
  CLI initially failed because the extracted archive has no .git directory;
  the scanner functions were then run against that explicit Git file list.
- Local working tree: full Python suite 162 passed; coverage 82.43%; Ruff lint
  and traceability integrity check passed; 176 definitions and 162 test nodes
  collected by the traceability check. Collection is not acceptance.
- GitHub main CI run 33317481447: completed success at the reviewed main SHA.
- PR #8 checks: firmware-check, python and repository-safety passed at the
  remote PR head. It remains draft, with no reviews or comments at inspection.
- Application/firmware/watchdog reviewers performed synthetic SQLite,
  mocked-client, mocked-relay and scratch-artifact probes. No real GPIO,
  production MQTT, live database, signing keys or OS credentials were used.

No fresh firmware compilation, USB bench, live relay test, clean-host install,
full-history secret scan, production load test, or package vulnerability scan
was performed in this review. gitleaks, pip-audit and bandit were not installed
in the inspected environment. Existing CI secret scanning is not a substitute
for claiming a fresh independent full-history scan.

## GitHub governance: verified current settings

- Main branch protection: API explicitly reports Branch not protected.
- Repository rulesets: none returned.
- Actions allowed: all; SHA pinning required: false.
- Default workflow token: read; workflow approval of PR reviews: false.
- Secret scanning and secret push protection: enabled.
- Dependabot security updates: disabled; alerts API reports alerts disabled
  and access/scope limitations. No vulnerability inventory was obtained.
- No releases returned; no open issues returned. No issue/release was created.
- Repository has MIT license; description is empty and topics are empty.

Recommended controls: protect main with required checks and a reviewed merge
path appropriate to a single-maintainer project; disallow force pushes; enable
dependency alerting and controlled update PRs; pin third-party Actions to
reviewed commits; archive release provenance. Do not enable noisy unattended
firmware/dependency rollouts into the live fleet.

## Severity interpretation

P1: high-priority correctness, security or recovery risk; fix before expanding
release automation. P2: material reliability/test/deployment debt. P3: usability
and maintainability improvements. Severity does not imply observed exploitation.
Findings below are published-main findings unless explicitly qualified.

## P1 — Recovery and trust-boundary findings

### A. Watchdog can cut power to a working hub

Location: tools/pi_watchdog.py:110-137; runbook: docs/operations-runbook.md:50-56.

Code declares healthy only when gateway, hub ping, SSH and API all succeed.
Any single failure increments the same recovery counter; once the threshold
is met and the gateway responds, a relay cycle is eligible. The runbook instead
says ping, SSH and dashboard must all fail. A blocked SSH port or stale sensor
fleet can therefore qualify an otherwise functioning hub for abrupt power loss.
Failures also accumulate while the gateway is unavailable.

A mock decision-loop probe with working target ping/API but failed SSH invoked
the mocked power_cycle at the threshold. No real relay ran. The reviewed local
watchdog source is byte-identical to published main, but this review did not
verify the remotely installed script/configuration.

Fix: separate availability, fleet health, management reachability and recovery
eligibility. Require corroborated hub failure; suspend/reset qualification when
network evidence is unavailable. Test the full matrix with mocked relay effects.
Persistent cooldown across monitor restarts and maintenance inhibition belong
in the same explicitly reviewed safety contract.

### B. Payload identity bypasses topic-level isolation

Location: app/iot_home/collector.py:73-93,149-175.

The callback trusts payload.deviceId and never matches it to the MQTT topic
segment. An authenticated device confined by ACL to its own topic can name
another device inside JSON, changing that other device's readings or status.
An isolated execution of the real callback demonstrated this. Per-device ACL
migration alone does not close the gap. Device-ID pattern/type checks are also
missing, despite the stated requirements.

Fix: validate JSON object shape, bounded typed ID and topic shape; enforce exact
identity equality before mapping, retirement decisions or persistence. Add
telemetry and status mismatch tests proving no relevant table changes and
continued processing of later valid messages. Local collector differs from
main, but prior local traceability still records these controls as missing;
recheck against the exact candidate when implementing.

### C. One persisted timestamp can break fleet-wide API responses

Location: collector.py:73-93; dashboard.py:94-110,1847-1854,1923-1926.

A timestamp such as 0001-01-01T00:00:00+01:00 passes ingestion; normalization to
UTC underflows. A synthetic DB and the real handler reproduced OverflowError
before response bytes were written. One bad current row prevents complete
latest/location responses until replaced; restarting the dashboard does not
repair persisted data. Requires malformed or malicious accepted sender input;
it is not an unauthenticated arbitrary database-write claim.

Fix: validate timestamp syntax/range at ingress; preserve the intentional
pre-NTP sentinel; catch normalization overflow and isolate bad rows so the
fleet endpoint cannot be disabled by one device. Test persisted malformed data.

### D. Published reading freshness is confused with status freshness

Location: db.py:251-275,369-397; dashboard.py:108-135;
watchdog tools/pi_watchdog.py:52-68.

Status updates refresh devices.updated_at; the API derives age from it rather
than independent telemetry receipt. Old telemetry plus a fresh status produced
stale=false and ageSeconds=0. Even offline status made the watchdog report a
fresh row in an isolated probe. This can mask failed sensors and make the
watchdog's freshness classification misleading.

Important distinction: local branch/working tree already separates telemetry
and device timestamps. Preserve and review that fix rather than reimplementing
it or reporting it as absent everywhere. Retained status is still not proof of
a new physical connection. Review summary aggregates and status-only devices.

## P2 — Reliability, security hardening and failure paths

### E. OTA staging can damage an existing published release

Location: app/iot_home/publish_ota.py:171-213; same file locally.

The binary is copied into the release directory before signing completes.
A failed restage left a new binary with the old manifest in a scratch probe.
Concurrent readers can also encounter incomplete copy output. Signature checks
should reject mismatches: this is a distribution/provenance failure, not an
arbitrary-image authenticity bypass.

Fix: validate inputs, stage/sign/verify privately, then atomically publish an
immutable release; reject accidental version reuse. Add failure-injection and
concurrent-reader tests.

### F. Deduplicated telemetry still rewrites device state

Location: app/iot_home/db.py:195-248.

The history insert ignores duplicates, but the device upsert still executes.
Telemetry, offline status, identical telemetry replay produced one reading
but changed online back to true. Older duplicates can regress newer metadata.

Fix: distinguish newly inserted readings from known duplicates before updating
current state. Model any connectivity observation separately; retain the
intentional sentinel exception. Verify both published and newer local DB code.

### G. Clearing a location override leaves the old effective location

Location: collector.py:137,157-161; dashboard.py:153-160,1974-1981;
locations.py:49-56.

Collector caches mappings and persists the substituted override as reported
location. Clearing the JSON override therefore falls back to the old stored
value, while collection can continue applying the cached override. Probe
confirmed configuredLocation=null but the old effective/reported location.

Fix: retain original reported location and resolve overrides at read time,
or introduce an explicit cache-reload/raw-value policy. Test save/change/clear
across subsequent ingestion without requiring an undocumented restart.

### H. Maintenance mistakes concurrent appends for lost history

Location: app/iot_home/db_maintenance.py:88-93; same file locally.

Separate before/after counts do not share a stable snapshot. A legitimate
append from a second connection caused the preservation assertion to fail,
skipping later backup/capacity checks. No data was deleted in the probe.

Fix: use snapshot/append-aware preservation validation and deterministic
concurrent-writer tests; do not disable the preservation requirement.

### I. Authentication has uncontrolled Unicode error paths

Location: app/iot_home/dashboard.py:200-225.

hmac.compare_digest on non-ASCII strings raises TypeError. UTF-8 Basic input
or a Unicode capability query can drop its request instead of returning 401.
This is not an authentication bypass or demonstrated whole-server crash.

Fix: compare correctly encoded bytes or enforce a consistent ASCII policy
for both configuration and input; align browser Basic encoding and test 401s.

### J. Sensor failure lacks a bounded diagnostic heartbeat/recovery policy

Location: firmware/src/main.cpp:502-517,1124-1143.

A Wi-Fi/MQTT-connected node resets the network recovery timer even when DHT
reads keep failing. Failed/rejected samples return before publishing. Diagnostic
counters are unavailable remotely during sustained failure; the periodic safety
reboot can be days away. This matches the class of online-but-silent symptoms,
but does not establish the cause of any particular physical sensor failure.

Fix: track time since a valid sample; emit bounded fault heartbeats without
relabeling stale measurements as fresh. Consider tested sensor reinitialization
and rate-limited recovery; physical wiring faults still need physical repair.
No firmware change goes to the fleet without the exact binary's bench gate.

### K. Watchdog input and cooldown semantics need hardening

Location: tools/pi_watchdog.py:58-68,95-98; deploy/pi-watchdog.service:10-11.

Malformed list rows such as null can throw AttributeError. Negative ages count
as fresh. Integer floor division accepts one fresh device out of three; call it
pipeline activity if intentional, not majority fleet health. Recovery cooldown
is in memory and resets on process restart.

Fix: validate response shapes/ages, explicitly define active/retired fleet and
threshold policy, persist recovery history safely, and test restart behavior.

### L. Synchronous OTA has no absolute download deadline

Location: firmware/src/main.cpp:803-805,842-869,922-931,1111-1122.

Each successful stream write resets the inactivity timeout. A slow trickle can
hold the synchronous callback for an unbounded total time, blocking normal
sampling/MQTT/recovery work. Final signatures protect authenticity, not this
availability failure.

Fix: absolute duration/throughput limits and a bounded state machine, without
interrupting critical flash finalization. Validate on the bench first.

### M. Published TLS installer can leave an unvalidated pending configuration

Location: scripts/configure_mosquitto_tls_acl.sh:62-85.

Published script invokes mosquitto -t, unsupported by the available 2.0.21
binary (safe /dev/null probe exited 3). It writes persistent files before this
failing gate, leaving pending state for a later restart. Local script differs
and includes compatibility work: inspect and preserve those changes.

Separately, published wildcard key permissions give the mosquitto group access
to ca.key (script:18-24,80-82). The broker needs its server key, not CA signing
authority. Treat local effective permissions as unverified, not newly exposed.

Fix: stage configuration, validate with a supported isolated method, install
with rollback, and keep the CA private key root-only/outside broker access.

### N. Dashboard history polling multiplies avoidable load

Location: app/iot_home/dashboard.py:1742-1764,1787,1862-1877.

Each tab fetches up to 50,000 history rows every three seconds. A synthetic
maximum response was about 10.5 MB and took 0.425 seconds to query/serialize
in the reviewer probe. This is measured cost, not a production outage or a
claim about normal response size. Overlap and multiple tabs amplify it.

Fix: slower independent history polling, serialized refresh, incremental or
cached results, chart downsampling, and visible truncation semantics.

## P2/P3 — Deployment, verification and maintenance process

- Installers/units hardcode account/checkout/runtime assumptions. Establish one
  supported virtualenv/package installation path, parameterize paths/users,
  and test clean install and in-place upgrade. enable --now does not itself
  reload code in an already-running service. Verify environment-file encoding
  rather than assume shell escaping equals systemd syntax.
- Backups use sound SQLite online backup/integrity checks, but the off-site
  job is time-separated rather than dependent on a successful fresh export.
  Checked-in backup roots alone do not establish recovery of protected broker/
  service configuration. Private excludes/key escrow/actual backup state were
  not inspected. Demonstrate complete clean-host recovery, separate signing-key
  escrow, and explicit archive retention without pruning historical readings.
- Add real broker-to-collector ingestion/LWT/dedupe tests; existing real broker
  ACL tests are valuable but do not cover the full ingest pipeline.
- Add disposable-key real-signature verification and HTTP symlink traversal
  tests. Mock signing tests prove orchestration, not cryptographic validity;
  missing symlink evidence is not a demonstrated traversal vulnerability.
- Pin/record tool and dependency versions. CI checks one Python version despite
  a broad >=3.11 declaration. Third-party Actions use mutable tags.
- Archive clean sample-build firmware/hash/commit/tool versions in CI with
  retention and explicit sample-versus-production labeling. No release evidence
  upload currently closes that requirement.
- Reconcile CI push filters with the actual agent branch naming; PR checks
  remain enabled. Add branch protection and traceability enforcement in stages.
- Extract embedded dashboard assets/shared MQTT setup only after behavioral
  regression coverage; avoid burying urgent correctness fixes in a rewrite.
- Reconcile stale runbooks/status wording, authentication descriptions and
  firmware download examples. Keep current policy separate from dated evidence.
- Phase-1 traceability is local-only/untracked. Its 176-ID mapping is useful but
  does not certify acceptance. Publish a reviewed sanitized foundation in a
  dedicated change, preserving unrelated user work.

## Strengths worth preserving

- Parameterized SQL, WAL, per-request connection lifecycle and transactions.
- Numbered migrations with concurrent-start locking, newer-schema rejection,
  rollback tests, and preservation of historical duplicate values.
- Real isolated-broker ACL delivery/forwarding matrix; operator-only commands.
- Native-testable filter, publish-policy, OTA-manifest and provisioning logic.
- Signed metadata plus image SHA/signature verification, gate ordering and
  monotonic anti-rollback. No arbitrary-image acceptance was demonstrated.
- USB provisioning bounds/identity binding, hidden password entry and separate
  provisioning versus anti-rollback state.
- Exact-artifact bench gates and dated release/soak evidence, correctly treated
  as historical rather than current validation.
- Dashboard authenticated mutations, bounded queries/body, path containment,
  query-secret redaction, atomic locked mapping writes and DOM text APIs.
- MIT license, repository privacy/secret controls, and explicit acknowledged
  transitional choices rather than undocumented claims of complete hardening.

## Recommended implementation sequence

1. Establish a reviewed release baseline: preserve user work, separate main/PR/
   local changes, checkpoint traceability, and protect main with existing checks.
2. Fix watchdog recovery eligibility and collector identity/timestamp handling
   in separate narrowly scoped, failing-first tested changes. Do not toggle the
   production relay or restart collection without explicit activation approval.
3. Preserve/promote the existing telemetry-freshness fix through review, rather
   than duplicating it; add hub-versus-fleet decision tests.
4. Make OTA releases atomic/immutable and make maintenance append-safe.
5. Add boundary tests and complete install/upgrade/full recovery drills.
6. Reconcile specs/runbooks and enforce mapping/release provenance in CI.
7. Refactor UI/transport structure and complete separately approved credential/
   TLS migrations and firmware diagnostic improvements.

Each change should state intended behavior, exact source/tests, candidate
fingerprint and results, rollback/activation plan where applicable, and remaining
gaps. Do not combine a firmware release, OS maintenance, broker migration and
application activation into one unattended operation.

## Review boundaries

No repository settings, source, runtime configuration, services, MQTT messages,
credentials, GPIO or firmware were changed by the review. Only scratch review/
test artifacts and this review report were written. Do not infer the remote
watchdog's installed code from a matching local source file. Dependency alerts
being disabled is a control gap, not evidence of a specific known CVE. This is
a broad critical review, not an exhaustive formal security audit.
