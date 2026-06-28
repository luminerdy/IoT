# Hardware Notes

## Raspberry Pi

Current project host:

- Hostname: `IoT Pi`
- Architecture: `aarch64`
- Kernel family observed: Raspberry Pi Debian
- Intended role:
  - MQTT broker
  - Collector service
  - SQLite database
  - Dashboard
  - Firmware/OTA server

## ESP32 Devices

Current known sensor platform:

- ESP32 development boards
- DHT22 temperature/humidity sensors
- Existing firmware was Arduino-based

Future firmware should:

- Use no local OLED/display.
- Publish to local MQTT.
- Use stable device ID in topics.
- Let the Pi own room/location mapping.
- Support OTA from the Pi after MVP.

## USB-Connected Test ESP32

Intent:

- Keep `Bench Device` connected to the Pi for firmware development and testing.
- Use it to validate builds and new features before OTA rollout to the rest of the fleet.
- Use USB flashing as the recovery path if OTA fails.

Current status:

- Bench device: `Bench Device` / `esp32-device-id`.
- After changing USB cords, the ESP32 is visible as a Silicon Labs CP210x USB serial bridge.
- The serial device is `/dev/ttyUSB0`.
- Device permissions are `root:dialout` with mode `0660`.
- User `scotty` has been added to the `dialout` group at the account level.
- `esptool` is installed in the project virtual environment at `.venv/bin/esptool`.
- PlatformIO Core is installed in the project virtual environment at `.venv/bin/pio`.
- PlatformIO detects `/dev/ttyUSB0` as `CP2102 USB to UART Bridge Controller`.

Verified chip probe:

```text
Chip type: ESP32-D0WDQ6 (revision v1.0)
Features: Wi-Fi, BT, Dual Core + LP Core, 240MHz
Crystal frequency: 40MHz
MAC: <device-mac>
Local device ID: esp32-device-id
```

Serial log check:

- Read `/dev/ttyUSB0` at 115200 baud for 10 seconds.
- No firmware log lines were emitted during that window.

Follow-up checklist:

- Start a fresh login shell if a terminal still does not show `dialout` in `groups`.
- Re-run:

```bash
ls -l /dev/ttyUSB0
lsusb
```

- Once visible, install/check tooling:

```bash
esptool.py --port /dev/ttyUSB0 chip_id
.venv/bin/esptool --port /dev/ttyUSB0 chip-id
pio device list
.venv/bin/pio device list
```
