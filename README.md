# EcoTech Marine Radion XR15w G5 Pro — Home Assistant BLE Integration

Control your **EcoTech Marine Radion XR15w G5 Pro** aquarium light via Bluetooth Low Energy from Home Assistant — with no official API, no cloud, no Mobius app required.

This project was built by **reverse-engineering the undocumented Mobius BLE protocol** (C2 protocol over GATT).

---

## How it works

```
Home Assistant ──HTTP──► BLE Bridge (xr15_server.py) ──BLE──► XR15w G5 Pro
 (custom component         runs on the Docker host,       Mobius C2 protocol
  or rest_command)         or any Pi near the tank
```

All Bluetooth work happens in `xr15_server.py` — a small HTTP server talking plain `bleak` → BlueZ. Home Assistant (native custom component, recommended — or plain `rest_command`) only makes local HTTP calls to it. Keeping HA's own Bluetooth stack out of the control path entirely is deliberate: it is by far the most reliable architecture of everything tried, especially with HA in Docker.

**Turn off** = write an all-zero schedule to the device → schedule plays silence  
**Turn on** = restore the original schedule → light resumes normal program

---

## Protocol notes (reverse engineered)

| Field | Value |
|---|---|
| BLE Address | your device's MAC |
| GATT Service prefix | `01ff01XX-ba5e-f4ee-5ca1-eb1e5e4b1ce0` |
| TX characteristic | `01ff0104` (write commands here) |
| RX characteristics | `01ff0101`, `01ff0102` (notify) |
| C2 magic (request) | `0xDE` |
| C2 magic (response) | `0xDF` |
| GET opcode | `0x17` |
| SET opcode | `0x18` (simple) / `0x1C` (sub-attr chunked) |
| Schedule attribute | `500` (Schedule1) |
| Intensity attribute | `511` (Schedule1Intensity) |
| Playback attribute | `510` (SchedulePlayback) |
| Slot count | 25 |
| Bytes per slot | 42 = `time(2B LE) + flags(1B) + 13×[vid(1B)+val(2B LE)]` |
| Channel IDs | `[21,23,18,17,19,20,31,32,22,16,1,101,100]` |
| MTU | 517 (auto-negotiated) |
| Batch size | 8 slots per write (≤ 352 bytes, safe within MTU) |

### Channel mapping (XR15w G5 Pro)

| ID | Channel |
|---|---|
| 21 | UV |
| 23 | Violet |
| 18 | Royal Blue |
| 17 | Blue |
| 19 | Green |
| 20 | Red |
| 31 | Unknown |
| 32 | Moonlight Blue |
| 22 | Warm White |
| 16 | Cool White |
| 1  | Brightness |
| 101 | Unknown |
| 100 | Unknown |

Values are 0–1000 (1000 = 100%).

---

## Requirements

- Raspberry Pi (tested on Pi 5) with Bluetooth
- Python 3.11+
- `bleak` and `aiohttp` libraries
- Home Assistant (any install type)

```bash
python3 -m venv ~/xr15-venv
~/xr15-venv/bin/pip install 'bleak==0.22.3' aiohttp
```

> ⚠️ The bleak version pin matters — see Troubleshooting. bleak 3.x fails to discover the light on hardware where 0.22.3 works instantly.

---

## Setup

### 1. Find your light's BLE address

```bash
sudo bluetoothctl
scan on
# look for "Mobius" or your device name
```

### 2. Decode your original schedule

The light's schedule is hardcoded in `xr15_server.py`. Before you can use **turn on**, you need to capture your device's current schedule and replace the `build_original_schedule()` function.

> **If you have the same schedule as mine**, the hardcoded values will work directly.  
> Otherwise, run a GET (opcode 0x17) against your device and decode the 25×42-byte response.

### 3. Configure the server

Edit `xr15_server.py` and set your device's MAC address:

```python
ADDRESS = "AA:BB:CC:DD:EE:FF"   # ← your XR15w MAC
PORT    = 8765
```

### 4. Run the server on the BLE Pi

```bash
python3 xr15_server.py

# Test it
curl http://localhost:8765/off
curl http://localhost:8765/on
curl http://localhost:8765/status
```

### 5. Install as a systemd service (auto-start)

```bash
sudo cp xr15.service /etc/systemd/system/
sudo systemctl enable xr15
sudo systemctl start xr15
```

Edit `xr15.service` to match your username and path if needed.

### 6. Add to Home Assistant

Add the contents of `ha_config.yaml` to your `/config/configuration.yaml`, replacing the IP with your BLE Pi's IP:

```yaml
rest_command:
  xr15_turn_on:
    url: "http://192.168.x.x:8765/on"
    ...
```

Restart HA, then add a button card:

```yaml
type: button
entity: switch.radion_xr15w
name: Aquarium
icon: mdi:fishbowl
tap_action:
  action: toggle
```

### 7. (Recommended) HA Custom Component

The custom component gives you real HA entities (light, color sliders, apply button) on top of the bridge. As of v2.0.0 it contains **no Bluetooth code at all**: all BLE work is done by `xr15_server.py` running directly on the host (plain `bleak` straight to BlueZ — the transport that has proven reliable), and the component talks to it over local HTTP. This deliberately keeps Home Assistant's own Bluetooth stack (and any Docker Bluetooth passthrough headaches) out of the control path entirely.

Setup: run `xr15_server.py` on the same machine as HA (steps 3–5 above — for HA in Docker with `network_mode: host`, the default bridge URL `http://127.0.0.1:8765` works as-is), copy `custom_components/mobius_xr15/` into your HA `config/custom_components/` directory, restart HA, then add it via **Settings → Devices & Services → Add Integration → "Mobius XR15"** and enter the light's MAC address (used as the device identity) and the bridge URL.

This adds a real `light.radion_xr15w_g5_pro` entity, plus a set of color-recipe entities:
- **On** installs the current color recipe (see below) across the device's original 11 time points and resumes playback — the day/night dimming shape from the original reverse-engineered schedule is preserved, but every point now carries the same flat color mix rather than a distinct ramp.
- **Off** writes an all-zero schedule.
- **Brightness** maps directly to the device's `Schedule1Intensity` attribute (0–1000 on the wire ↔ 0–255 in HA) — an overall multiplier on top of the recipe. Adjusting brightness while the light is already on only retargets intensity — it doesn't rewrite the schedule.
- State is optimistic (the device has no reliable readback over this protocol) and is restored across HA restarts.

The color recipe is 10 `number.*` entities, one per channel (UV, Violet, Royal Blue, Blue, Green, Red, Moonlight Blue, Warm White, Cool White, Brightness — the 3 unidentified protocol channels are left at 0 and not exposed), plus a `button.*` entity, **Apply Schedule**, that pushes the current values to the device immediately without needing a full off/on cycle. All of these appear automatically under the device's page (Settings → Devices & Services → Mobius XR15 device). Turning the light on always re-installs the current recipe, so edits persist across HA restarts the same way the light's own state does.

For day/night timing, use the auto on/off schedule below rather than editing per-time-of-day values — this integration intentionally doesn't expose per-slot editing (11 slots × 13 channels = 143 entities proved unwieldy in practice).

> ⚠️ Editing several sliders and then hitting **Apply Schedule** issues one full 25-slot BLE write (several seconds, ~6 packets). Don't wire anything to auto-apply on every single slider tick — batch your edits, then apply once.

**Daily ramp.** The light plays a *time-of-day* schedule and transitions between consecutive slots, which is how the Mobius app produces its gradual sunrise/sunset. The bridge writes the recipe across 11 time points with the master dimmer (channel 1) scaled by a daily curve — 20 % at midnight, rising to 100 % at 12:00–14:00, easing back to 10 % by 23:30 — while the colour channels stay fixed, so the colour balance is identical at every hour and only the brightness moves. Post `"curve": "flat"` to `/apply` for the older constant-output behaviour.

> Channel 1 gates everything: at 0 the light stays dark no matter what the colour channels say, which is why the UI calls it **Master Dimmer**. The daily curve scales relative to whatever you set it to, so a master of 600 peaks at 600.

A **Bridge Status** diagnostic sensor on the device page shows the outcome of every BLE command (`OK: off`, `FAILED: apply (intensity 1000)` with the error text as an attribute) polled from the bridge every 30 s, and the light/button entities go *unavailable* if the bridge itself stops responding. Since HA only talks HTTP, HA needs **no Bluetooth access at all** — no Docker Bluetooth passthrough, no HA Bluetooth integration, no ESPHome proxy. Only the host running `xr15_server.py` needs a working BlueZ + adapter in range of the light.

#### Troubleshooting (read this before blaming the code)

Hard-won lessons, in the order they will bite you:

1. **Pin bleak to 0.22.x** (`pip install 'bleak==0.22.3'`). The bridge was written against the bleak 0.2x API. bleak 3.x changed both the API and discovery behavior — on the same hardware where 0.22.3 connects in ~4 s, 3.0.2 fails every attempt with `Device ... was not found`.
2. **Corrupted BlueZ GATT cache** is the sneakiest failure: the light connects fine but its service list comes back without the `01ff0104` TX characteristic (`TX karakteristiği bulunamadı` / "TX characteristic not found"), every time, *surviving reboots*. Fix:
   ```bash
   bluetoothctl remove 84:25:3F:76:67:4C     # your light's MAC
   sudo systemctl restart bluetooth
   sudo systemctl restart xr15
   ```
3. **`Device ... was not found` while `bluetoothctl` can see the light** usually means something else holds the light's single BLE connection (it stops advertising while connected) — the Mobius app on a phone is the usual culprit; close it fully. Check with `bluetoothctl info <MAC>` (`Connected:` line).
4. **"Nothing happens" at night is often correct behavior.** `/on` installs the original *day/night ramp* schedule — at 22:00 that means moonlight at 15%, i.e. nearly dark. The flat recipe (`/apply`, or HA's Apply Schedule) shows the same mix at every hour — use it to verify the chain any time of day. And a recipe with all sliders at 0 is a faithful command to display darkness.
5. **`org.bluez.Error.InProgress` on every attempt, or commands that hang forever.** The adapter (or BlueZ's view of the device) is wedged — often after a connect that stalled and got cancelled. **The bridge now repairs this by itself**: after two consecutive failed jobs it power-cycles the adapter (`bluetoothctl power off/on`, the root-free equivalent of restarting the service) before the next attempt, and repeats that escalation while failures continue. Press the **Reset Bluetooth** button on the device page (or `curl -X POST http://127.0.0.1:8765/reset`) to force the same repair immediately. `consecutive_failures` in `/status` — and on the Bridge Status sensor — shows how deep it currently is. Only if all that fails is the manual hammer still available:
   ```bash
   sudo systemctl restart bluetooth      # xr15 restarts with it (PartOf=)
   ```
   Note the bridge deliberately never runs that itself: with `PartOf=bluetooth.service` it would kill its own process mid-command, and it needs root. The adapter power-cycle achieves the same reset without either problem.
   The bridge also defends itself here: every BLE job is capped at 120 s, a timed-out or `InProgress` attempt triggers `bluetoothctl disconnect` to clear BlueZ's pending operation, and the outcome is recorded so a stuck job can't silently block the queue behind it. If `curl .../status` ever shows `"ok": null` with a timestamp minutes (or days) old, that's the symptom this guards against.
6. **The bridge logs everything** — `journalctl -u xr15 -f` shows each connect attempt, packet write, and error in real time (the systemd unit runs Python unbuffered specifically so this works). `curl .../status` gives the last job's verdict, and the same thing appears in HA as the **Bridge Status** sensor.
7. **Read the device's actual state** when in doubt: `curl "http://127.0.0.1:8765/dump?attr=511&variant=3"` returns the light's stored intensity as a raw C2 response frame (attr 500 = schedule, 510 = playback). If your value reads back, the write path works and the problem is elsewhere.

#### Optional: maintenance reminders

`akvaryum_bakim_helpers.yaml` + `akvaryum_bakim_automations.yaml` add dashboard-driven maintenance tracking for three tasks (water change, filter cleaning, glass cleaning): a last-done date and an adjustable interval per task, a "days remaining" template sensor (negative = overdue), a one-tap "done today" script wired to dashboard cards that turn red when due, and a daily 10:00 persistent notification listing anything due. Paste the helpers into `configuration.yaml` (merging top-level sections with any you already have), append the automation to `automations.yaml`, and use the 🧽 BAKIM section in `dashboards/akvaryum.yaml` as the UI. Swap `persistent_notification.create` for `notify.mobile_app_*` to get reminders on your phone.

#### Optional: automatic daily on/off schedule

The device's own onboard schedule already ramps brightness up and down across the day once the light is on. If you also want it to turn fully on/off at set times (e.g. a full blackout overnight), two files are provided:

- `xr15_schedule_helpers.yaml` — two `input_datetime` helpers (`radion_xr15_acilis_saati` / `radion_xr15_kapanis_saati`) for the on/off times, adjustable from the dashboard. Paste into `configuration.yaml`.
- `xr15_schedule_automations.yaml` — two automations that call `light.turn_on`/`light.turn_off` at those times. Append to `automations.yaml`.

`dashboards/akvaryum.yaml` is an example Lovelace dashboard (Turkish) that ties it together — a `light` tile with brightness control, two `xr15-time-picker-card` cards for the on/off schedule, ten `xr15-channel-bar-card` color sliders, and the Apply Schedule button. It also references several sensors/switches specific to one particular aquarium setup (temperature probe, ATO controller, leak sensor, KH controller) — treat it as a template to adapt, not a drop-in file. The `number.*` entity IDs it references (e.g. `number.radion_xr15w_g5_pro_uv`) are HA's standard slug of the device + entity name — verify them against Settings → Devices & Services → Entities after setup and adjust if HA generated something different.

`www/xr15-time-picker-card.js` and `www/xr15-channel-bar-card.js` are small self-contained custom Lovelace cards (no dependencies, no build step):
- `xr15-time-picker-card.js` wraps the browser's native `<input type="time">` for an `input_datetime` entity. On iOS Safari this renders as the OS's native scrolling wheel picker; other browsers fall back to their own time control (a plain box on desktop Chrome, a clock dial on Android) — the wheel look is a browser/OS behavior, not something any Lovelace card can force everywhere.
- `xr15-channel-bar-card.js` wraps the native `<input type="range">` for a `number` entity, tinted via CSS `accent-color` to match the channel it controls (e.g. purple for UV, red for Red).

To use either:

1. Copy the `.js` file to your HA `config/www/` directory.
2. Add it as a dashboard resource: **Settings → Dashboards → 3-dot menu → Resources → Add Resource**, URL `/local/<filename>.js`, type **JavaScript Module**.
3. Use `type: custom:xr15-time-picker-card` or `type: custom:xr15-channel-bar-card` with an `entity:` (plus `color:` for the bar card) in a card, as done in `dashboards/akvaryum.yaml`.

---

## Files

```
.
├── xr15_server.py                    # BLE HTTP bridge (standalone script, for the rest_command setup)
├── xr15.service                      # systemd service for xr15_server.py
├── ha_config.yaml                    # HA configuration.yaml snippet for the rest_command setup
├── xr15_schedule_helpers.yaml        # optional: input_datetime helpers for auto on/off times
├── xr15_schedule_automations.yaml    # optional: automations that follow those helpers
├── dashboards/
│   └── akvaryum.yaml                 # example Lovelace dashboard (template, adapt to your setup)
├── www/
│   ├── xr15-time-picker-card.js      # optional: native-wheel time picker card for the on/off schedule
│   └── xr15-channel-bar-card.js      # optional: colored slider card for the color recipe
└── custom_components/
    └── mobius_xr15/                  # native HA integration (recommended)
        ├── manifest.json
        ├── __init__.py
        ├── config_flow.py            # UI setup: enter the light's MAC address
        ├── const.py
        ├── protocol.py               # pure C2 protocol packet builders (no I/O)
        ├── schedule.py               # builds the flat schedule from the color entities
        ├── client.py                 # BLE transport (bleak-retry-connector)
        ├── light.py                  # light.radion_xr15w_g5_pro entity
        ├── number.py                 # per-channel color recipe entities (10)
        ├── button.py                 # "Apply Schedule" action
        └── strings.json / translations/en.json
```

---

## Tested on

- EcoTech Marine Radion XR15w **G5 Pro**
- Firmware: (check your Mobius app)
- Raspberry Pi 5, Ubuntu/Raspberry Pi OS, BlueZ
- Home Assistant 2024.x (Docker)

> May work on other Radion models (XR30, XR15 G4, etc.) — channel count and slot format may differ.

---

## Contributing

If you have a different Radion model and want to add support, open an issue with:
- Your model name
- Number of channels
- Slot byte count (from a GET opcode 0x17 response)

---

## License

MIT

---

## Author

[@ugurbaykoc](https://github.com/ugurbaykoc)
