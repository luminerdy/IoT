# Critical Review Remediation — Implementation Plan

Date: 2026-11-19
Status: proposed implementation plan. Publication of these two documents was
authorized on 2026-11-20; no code implementation, settings change, merge or
live activation is authorized by this document.
Owner: PiIot coordinates engineering and verification; Scotty approves product
policy, publication/settings changes and disruptive activation.

## Purpose and relationship to existing work

Remediate the critical GitHub review while preserving the reporting fleet,
historical data and existing local fixes. This is the execution backlog for
the [critical review dated 2026-11-19](critical-review-2026-11-19.md). Finding letters A–N below identify review
findings, not permanent normative requirement IDs.

The local-only `docs/spec-alignment-implementation-plan.md` remains the
specification-program plan (not included in this documentation-only PR). Its Phase 1 is implemented locally; its Phases 2–5 remain pending. This
plan reuses that register and interleaves targeted specification reconciliation
with urgent correctness work. It does not repeat the completed inventory or
require all historical documentation to be perfected before a safety fix.

## Baseline and boundaries

Known review targets (refresh before implementing):
- Published main: `bab023cedeed334ae51eeda698db727938561fcf`.
- Draft PR #8/local committed branch: `f390e0b8aa5f1cc176e0e1596f56f5aadec0d6f1`.
- Local working tree: additional dashboard, monitoring, documentation and
  traceability changes; do not assume PR checks cover these.
- Remotely installed watchdog code/configuration: not established by source
  review. Local source equality is not deployment evidence.

Review test results are dated baselines, not future release clearance:
published main 127 tests/86.76%; local tree 162 tests/82.43%. Prior native
firmware baseline passed 24 cases, but static analysis emitted a HIGH
ArduinoJson preprocessing diagnostic despite a successful exit status.

Safety rules:
1. Preserve existing modifications/untracked files. Do not stash, reset,
   switch the live checkout, add all files, commit or push user work implicitly.
2. Develop in an isolated authorized branch/worktree, using a deliberately
   reviewed inclusion list for existing fixes. Avoid importing old release
   artifacts or private runtime files.
3. Use temporary DBs, isolated MQTT brokers, disposable keys and mocked relay
   operations. No malformed-message tests on production MQTT or live GPIO.
4. No historical row deletion. A needed migration has its own verified backup,
   scratch replay, value-preservation and rollback/forward-recovery gate.
5. Firmware needs exact-artifact USB bench approval before a separately
   approved fleet rollout. Do not test recovery by power-cycling the hub.
6. Code review approval, GitHub publication approval and production activation
   approval are separate gates. OS/Hermes updates are outside this project.
7. Never expose credential values, runtime IDs or private infrastructure in
   public requirements, logs, CI artifacts or tickets.

## Proposed policy decisions

Confirm these before implementing their behavior; none is silently accepted:
- Hub failure, management reachability and sensor-fleet degradation are distinct.
  A failed SSH/ping check alone, stale individual sensors, or a degraded fleet
  must not qualify a functioning dashboard hub for relay recovery.
- Conservative initial relay rule: gateway positively reachable AND target
  ping, SSH and application reachability all fail for the required consecutive
  checks, outside a maintenance window and persisted cooldown. Loss of gateway
  evidence suspends/resets qualification. Application-only recovery, if wanted,
  is a separate explicitly approved non-relay policy.
- An HTTP API that responds but has stale sensors is reachable/degraded, not
  equivalent to a dead hub. Identity mismatch is a separate security/network
  fault: alert and inhibit a blind cycle until a policy is approved.
- Preserve existing approved relay interval, power-off duration and cooldown
  unless a verified requirement change explicitly authorizes a new value.
- Cooldown persists through monitor process restart; invalid/missing state must
  not authorize an immediate extra relay cycle. Clock rollback/reboot and
  state-corruption behavior must be specified before implementation.
- Diagnostic heartbeats do not refresh measurement timestamps or replace values.
- Release version labels are immutable by default; no silent overwrite.
- Preserve manual dashboard tabs unless Scotty requests rotation again.
- Require checks on main without imposing an impossible independent-human
  approval rule on a sole-maintainer repository. Agree the exception path.

## Work packages and acceptance gates

### CR-00 — Establish a safe release baseline

Priority: first prerequisite. No production change.

Tasks:
- Refresh remote main/PR state, working-tree inventory and separate artifact/
  source hashes; inspect differences and record what is actually deployed
  read-only, without printing credential-bearing service/environment data.
- Review the local traceability foundation and existing freshness/TLS fixes;
  decide which are retained. Split unrelated UI/uptime work from safety fixes.
- Establish an approved integration branch and explicit file/commit inclusion
  list without altering the live checkout. Retain the original snapshots.
- Run Python/lint/format/traceability/privacy baseline and relevant native/
  firmware checks; record exact commit plus dirty-tree/artifact fingerprints.
- Create a sanitized prioritized backlog locally; GitHub issues/PRs only after
  publication approval. Do not require publication before developing fixes.

Acceptance: main, PR, local and deployed targets are distinguishable; existing
work remains recoverable; every subsequent change names its baseline.

### CR-01 — Targeted contracts and traceability updates

Priority: run alongside the initial fixes; depends on CR-00.

Tasks:
- Add/reconcile normative watchdog safety, maintenance, identity, input and
  persistent cooldown contracts and acceptance/test IDs through the existing
  spec process; allocate new permanent IDs only after checking definitions.
- Reconcile telemetry-vs-status age, timestamp validation/sentinel behavior,
  duplicate state updates and atomic immutable OTA publication.
- Keep lifecycle, implementation, available verification and executed evidence
  separate. Update the canonical register and regenerate the report per change.
- Record unresolved policy decisions explicitly. Do not downgrade a requirement
  merely to make an existing implementation compliant.

Acceptance: each urgent change has an intended contract, exact tests and a
reviewable requirement chain. This is spec-alignment Phase 2 incrementally,
not blanket completion of all specification work.

### CR-02 — Watchdog recovery safety

Finding coverage: A, K. Priority: urgent. Depends on CR-00 and selected CR-01 policies.

Tasks:
- Extract pure decision/state logic separating reachability, telemetry quality,
  management-port evidence and relay eligibility.
- Strictly parse API objects, missing/null rows, booleans/nonnumeric/negative
  ages, empty lists, status-only records and HTTP/timeouts.
- Explicitly define active/retired/bench membership and thresholds; do not
  confuse pipeline activity with a majority of the expected fleet.
- Add bounded maintenance inhibition with auditable expiry, persistent recovery
  records and safe clock/restart/corruption handling.
- Read back actual installed script/unit/configuration before preparing an
  activation package. Avoid exposing any secrets from those files.

RED-to-GREEN tests: healthy API with SSH down; healthy API with ICMP down;
stale fleet with reachable API; all target checks down with gateway up;
gateway loss/return; identity mismatch; malformed responses; threshold boundary;
cooldown, monitor restart, host reboot and maintenance expiry/state failure.

Acceptance: all unauthorized-cycle cases assert zero calls to mocked relay;
only the selected corroborated-failure policy permits one cycle; cooldown
survives restart. No live relay operation is needed to prove logic.

Activation gate: explicit approval, retained previous script/config, remote
pre/post health evidence, then observation in log-only/relay-inhibited mode
where feasible before separately enabling the approved recovery policy.
Changing relay inhibition itself requires approval; never leave it disabled
without an expiry, named owner and verified restoration procedure.

### CR-03 — Collector identity and timestamp boundary

Finding coverage: B, C. Priority: urgent. Depends on CR-00/CR-01.

Tasks:
- Validate JSON object shape, exact device-ID pattern/types, expected MQTT
  topic structure and topic/payload equality before all side effects.
- Reject booleans/nonfinite or out-of-range measurements, invalid sequence
  types/ranges and oversized fields using explicit compatibility-reviewed bounds.
- Validate/normalize timestamps with safe range handling; preserve legitimate
  pre-NTP sentinel behavior. Defensive API rendering must tolerate already
  persisted malformed rows without deleting history.
- Update simulator/fixtures to valid synthetic IDs and matching publish policy.
  Keep ingestion failures controlled and safe logs free of secret payloads.

RED-to-GREEN tests: telemetry/status cross-identity attempts, malformed object/
ID/topic, null/nonnumeric/nonfinite fields, integer binding bounds, timestamp
underflow/overflow/offset/sentinel, poisoned DB rows and subsequent valid input.
Assert no rejected-message effects on readings/devices/deployment attempts.

Acceptance: no topic identity impersonation; bad timestamps cannot disable
fleet APIs; valid deployed message shapes remain accepted. Run an isolated
real-broker test; no production fault injection.

Activation: explicit collector/dashboard restart approval with existing backups
and exact previous runtime artifact available. No schema migration is assumed.

### CR-04 — Preserve freshness and make current state replay-safe

Finding coverage: D, F. Priority: high. Depends on CR-03 contract; can develop
in parallel with CR-02 using owned files/reviewed integration boundaries.

Tasks:
- Review and retain existing local telemetry/device timestamp separation rather
  than reimplementing it. Publish/promote it only through the release gate.
- Treat retained status, live status and accepted new measurements distinctly.
  Current dashboard summaries must not silently present stale values as current.
- Avoid replacing newer device state with historical duplicate telemetry;
  document ordering and connectivity semantics explicitly.
- Align watchdog/API contract with actual telemetry receipt and real readings.

Tests: ancient telemetry + online/offline/retained status stays stale; status-
only device not fresh; duplicate after offline and after newer telemetry cannot
regress state; intentional pre-NTP dedupe exemption remains valid.

Acceptance: independent connection/fleet health is visible and tested; no loss
of historical readings and no accidental double application of the local fix.

### CR-05 — Atomic immutable OTA releases and real cryptographic verification

Finding coverage: E; signing-test gap. Priority: high. Depends on CR-00/CR-01.

Tasks:
- Validate inputs before altering any published directory.
- Stage binary/manifest and produce signatures privately on the same filesystem;
  verify the complete pair, then publish atomically with an immutable label.
- Define concurrency/locking, cleanup, fsync/durability expectations and safe
  retry behavior. A failed operation preserves the prior release byte-for-byte.
- Use disposable keys for independently verified image/metadata signatures;
  no changes to production signing keys or signing backend solely for testing.

Tests: missing key, sign failure, invalid version/build/URL, interrupted staging,
existing-label collision, concurrent reader/writer, correct and wrong keys,
tampered binary/metadata and metadata canonicalization.

Acceptance: failure cannot corrupt a published release; real signatures verify;
production artifacts and keys are untouched. Never call a sample CI build a
bench-approved release. Publishing code does not authorize an OTA command.

### CR-06 — Remaining application integrity fixes

Finding coverage: G, H, I. Priority: next, in separate small review units.

Tasks:
- Location mapping: retain raw reported values, resolve overrides consistently,
  eliminate stale cached overrides on save/change/clear. Assess migration needs;
  do not invent historical raw locations that were previously overwritten.
- Maintenance: use a consistent snapshot or append-aware preservation strategy
  that detects deletion/value loss without treating legitimate growth as loss.
- Authentication: compare correctly encoded bytes or enforce a declared ASCII
  policy consistently; return controlled failures on Unicode/malformed input.

Tests: mapping save/change/clear through ingestion without undocumented restart;
real second-connection append and simulated loss; Unicode credentials/keys,
invalid Base64 and correct/wrong/missing auth returning expected status codes.

Acceptance: each reproduced failure has its own regression; no weakened auth,
no deletion of history, and no suppression of backup/capacity checks merely
to hide an inconsistent preservation assertion.

### CR-07 — Boundary tests and CI/GitHub controls

Priority: begin narrow tests with each fix; expand after CR-02–CR-06.

Tasks:
- Real isolated broker -> collector -> temporary SQLite tests: valid ingest,
  LWT/offline, reconnect, duplicate delivery, identity rejection and continued
  valid traffic. Keep explicit test endpoints separate from production.
- Real HTTP encoded traversal and symlink-escape tests; browser tab/keyboard/
  refresh/scroll checks for retained UI behavior.
- Enforce traceability inventory/reference/report checks and a visible legacy
  gap baseline. Prevent unexplained new gaps; do not equate checker success
  with product compliance or ignore skipped prerequisite-dependent tests.
- Reconcile branch triggers; pin reviewed Actions/dependencies/tooling, choose a
  supported Python matrix, record resolved versions and cap parallel test cost.
- Archive clean sample firmware binary/SHA/commit/tool versions with a reviewed
  retention policy and privacy scan. Diagnose the known cppcheck preprocessing
  limitation explicitly rather than masking HIGH findings behind exit zero.
- With separate settings approval, protect main and required check names,
  disable force-pushes, retain read-only workflow tokens, enable dependency
  alert/update review and preserve secret scanning/push protection.

Acceptance: a removed mapped test/reference fails CI; changed behavior has
real boundary coverage; archived artifacts have honest provenance; approved
GitHub settings are read back on the exact target after writes. No automatic
merge or unattended fleet deployment is introduced.

### CR-08 — Reproducible installation and complete recovery

Finding coverage: M; install/backup process findings. Priority: before calling
the repository a reproducible deployable release.

Tasks:
- Parameterize user/path/ports and select one supported runtime environment;
  test clean install and already-running-service upgrades outside production.
- Test systemd environment-file serialization with disposable unusual inputs;
  do not assume shell %q escaping is a systemd serialization contract.
- Preserve local Mosquitto compatibility improvements; stage/validate supported
  broker config before replacement, with rollback on any failed gate.
- Keep CA signing key root-only and separate from broker-readable server keys.
  Inspect actual permissions read-only before recommending any rotation.
- Chain off-site backup to a successful fresh verified export. Specify protected
  broker/service configuration coverage and separately approved key escrow.
- Verify restore completeness/freshness and explicit compressed-backup retention.
  Deleting backups or altering schedules requires its own approval; historical
  database rows remain preserved.

Acceptance: a disposable host/image can install, upgrade and restore broker,
collector, dashboard, config and data from documented artifacts; wrong config
or failed export leaves the prior working state intact. Capture restore evidence,
not just archive presence. No production broker restart during the drill.

### CR-09 — Firmware sensor diagnostics and bounded OTA availability

Finding coverage: J, L. Priority: after host-side safety improvements; distinct
firmware release workstream, never bundled with a broker migration.

Tasks:
- Specify fault heartbeat and time-since-valid-sample separately from telemetry.
  Preserve cumulative diagnostics without labeling old samples as fresh.
- Evaluate DHT reinitialization/backoff and optional rate-limited recovery using
  fault-injection evidence; do not assume a reboot fixes damaged wiring.
- Bound total OTA duration/minimum progress while respecting safe flash
  finalization and existing signed verification/anti-rollback contracts.
- Review NVS anti-rollback persistence failures and define fail-safe behavior.
  Revisit thermal plausibility cutoff only as a separate product decision;
  the existing cutoff is deliberate, not an incidental bug to silently change.

Tests: native fault-state policy plus exact-binary USB bench tests for sustained
sensor failure, restoration, no stale-value freshness, slow-trickle OTA,
normal signed OTA, invalid signatures, same/older build rejection and recovery.

Acceptance: no unbounded OTA stall, bounded honest diagnostic output, preserved
security gates; exact binary/hash/build and soak evidence recorded. Deploy only
with separate bench and one-device/small-batch rollout approvals, with a stop
on any missing terminal OTA acknowledgement or failed return to fresh data.

### CR-10 — Dashboard efficiency, maintainability and documentation closure

Finding coverage: N; remaining P3/documentation findings. Priority: after
behavioral regression protection, not a prerequisite to urgent fixes.

Tasks:
- Separate latest and history refresh cadence, prevent overlaps, implement
  incremental/cache/downsample choices and signal truncation explicitly.
- Benchmark representative and upper-bound history loads/multiple clients
  using synthetic data; set justified budgets rather than copy one probe time.
- Extract static UI assets and shared MQTT setup incrementally with browser/API
  contracts intact. Do not combine these with unrelated security rewrites.
- Reconcile install/operations/security/OTA runbooks and current target/deployed
  status; mark dated observations historical and remove obsolete next steps.
- Complete spec-alignment Phases 2–5 and regenerate traceability as contracts
  change; distinguish deliberately deferred product requirements from closure.

Acceptance: measured load improves with equivalent chart semantics; browser
behavior remains correct; one clear operational entry point; outstanding gaps
and deliberate product choices remain visible.

## Finding-to-work mapping

- A -> CR-02
- B -> CR-03
- C -> CR-03
- D -> CR-04 and CR-02
- E -> CR-05
- F -> CR-04
- G -> CR-06
- H -> CR-06
- I -> CR-06
- J -> CR-09
- K -> CR-02
- L -> CR-09
- M -> CR-08
- N -> CR-10
- Governance, artifact provenance and dependency controls -> CR-07
- Install/backup/recovery completeness -> CR-08
- Boundary-test gaps -> CR-03/CR-05/CR-07
- Release drift/local-only traceability -> CR-00/CR-01
- Documentation/architectural maintainability -> CR-01/CR-10

## Review and verification checklist for every implementation unit

1. Confirm exact baseline and intended requirements; write failing regression
   first, observe the expected failure, implement minimal fix, then refactor.
2. Run focused tests, full configured Python suite (>=80% gate), lint/format,
   traceability generation/check and repository identifier checks as relevant.
3. Run native/compile/static firmware checks for affected firmware contracts;
   inspect warnings and diagnostic severity, not exit status alone.
4. Record exact candidate commit/diff and artifact hashes, test commands,
   results, skips and limitations; never reuse stale green CI as proof.
5. Independent review covers security, logic, preservation, compatibility,
   operational rollback and spec/test mapping. Changes only within approved scope.
6. Prepare narrowly scoped commit/PR only after publication approval; do not
   stage local-only instructions, private review artifacts or unrelated changes.
7. Read back any GitHub changes. For activation, capture pre/post health on the
   exact deployed component and verify the effective version, not only disk files.

## Activation, rollback and observation

- No activation during implementation tests. Obtain approval naming component,
  expected interruption, maintenance/watchdog coordination and observation owner.
- Save previous code/config checksums and a fresh restore-verified DB backup
  when data/schema risk exists. Review effective systemd runtime/environment
  without exposing secrets.
- Watchdog activation is separate from collector/dashboard activation. Any relay
  test requires another explicit approval; normal deployment need not cycle it.
- A DB migration prevents blind code-only rollback. Pre-test compatible rollback
  or forward repair on scratch restores without discarding newly collected rows.
- Roll back or pause on lost collection, API failure, newly rejected valid
  devices, unexpected relay eligibility, backup errors or missing OTA lifecycle.
- Recommended host-side observation: verify immediately and across several
  normal reporting intervals, then review a 24-hour window. Firmware soak and
  rollout use the existing exact-artifact gate and stop conditions. Observation
  is not automatic unless a verified scheduled mechanism has been enabled.

## Suggested start and approval checkpoints

Start CR-00 now only after implementation is authorized; then run targeted
CR-01 contracts with CR-02 watchdog and CR-03 collector changes. These are the
first safety deliverables. CR-04/CR-05 follow, then remaining application/test/
deployment work. CR-07 governance can progress alongside after settings approval.
CR-09 and CR-10 are later releases, not conditions for closing urgent P1 fixes.

Approval checkpoints:
- Development start and isolated workspace/inclusion list.
- Selected watchdog/product policies.
- GitHub commits/push/PRs/settings.
- Each production activation, broker/backup policy change and firmware gate.

Completion means the reproduced review failures are fixed and tested on the
exact candidate, publication/deployment status is explicit, and remaining
product gaps have an accepted disposition. No blanket statement of full system
security or compliance follows merely from closing this backlog.
