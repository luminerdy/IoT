# Session Handoff

Last updated: 2026-07-12

## Current State

The local-first IoT stack is running on the Pi. Mosquitto, the collector, and
the dashboard are active. All 23 mapped devices are online and non-stale.
Seven devices are on `0.1.5-led-off`; 16 remain on `0.1.4-antirollback`.

The `0.1.5-led-off` firmware removes onboard LED flashes from telemetry and
MQTT failure paths. The exact signed build `2026071201` passed a USB bench
flash and full report interval on Sunroom Test, then reached Den, Kitchen,
Office, FrontBedroom, Entryway, and Laundryroom successfully.

The rollout is paused at MasterBedroom. It remains healthy on the old firmware
but reconnects to MQTT frequently and did not complete OTA. ESP32 clients also
failed to fetch through `iot-pi.local`; the successful batches used
`http://<pi-lan-ip>:8000`. Require per-device `downloading → rebooting` status
and fresh target-version telemetry before expanding future batches.

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

The expected live state is 23 mapped devices, no `UNMAPPED` rows, 7 devices on
`0.1.5-led-off`, 16 on `0.1.4-antirollback`, and all devices online/non-stale.
