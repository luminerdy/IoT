# Session Handoff

Last updated: 2026-07-10

## Current State

The local-first IoT stack is running on the Pi. Mosquitto, the collector, and
the dashboard are active. The live mapped fleet contains 23 devices on
`0.1.4-antirollback`, including `Attic`, `AtticChimney`, and `AtticDoor`.

Uncommitted work adds a dedicated Attic graph group, alphabetical device-card
sorting, hottest-first Latest Readings, and graph reference lines at 75 F and
100 F. The specs, tests, and operating docs were updated with this behavior.

## Attic Observation To Follow Up

On 2026-07-10, `Attic` peaked at 137.5 F around 15:21 CDT, stopped reporting
after 15:22, and returned around 18:34 at 124.3 F. The outage lasted about
3 hours 12 minutes and began before the Pi reboot at 17:33. `AtticChimney` and
`AtticDoor` did not show the same device-specific gap. Sequence resets before
the outage suggest rebooting or unstable power; high temperature is correlated
but not proven as the cause.

Watch the sensor during the 2026-07-11 afternoon heat window. If it repeats,
compare the failure temperature and inspect the power supply, regulator,
wiring, and enclosure.

## Verification

Run:

```bash
cd /home/scotty/IoT
.venv/bin/python -m pytest
python3 -m compileall app scripts
curl -fsS http://127.0.0.1:8000/api/latest
```

The expected live state is 23 mapped devices, no `UNMAPPED` rows, and all
three attic locations online when their most recent reports are fresh.
