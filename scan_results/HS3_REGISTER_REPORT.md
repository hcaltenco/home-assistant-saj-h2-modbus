# SAJ HS3 Register Verification Report

**For:** [Issue #202 — HS3 register verification](https://github.com/stanus74/home-assistant-saj-h2-modbus/issues/202)
**Author:** @hcaltenco
**Date:** 2026-10-04 (updated 2026-10-07 with write-control verification)
**Status:** Six-state scan complete. Full read/write control verified: strategy switching, power limits, schedule management, start/stop.

---

## Device Information

| Field | Value |
|-------|-------|
| Inverter model | SAJ HS3-10K-T2-W-PX |
| Inverter firmware | Display: V2.1.20 (0x0848), Master: V2.1.30 (0x0852), Slave: 0xFFFF |
| Serial number | PBT2103J250707E1A00650 (decoded from 0x8F03–0x8F16) |
| Product code (0x8F0D) | 12592 (0x3130, ASCII "10") |
| EV Charger model | CU2-11K-T-I (11kW, decoded from 0x3034–0x3039) |
| EV Charger serial | E2AS113A2506E00005 (decoded from 0x3024–0x302C) |
| EV Charger firmware | 1.6.78 / 1.0.02 (decoded from 0x303C–0x3043) |
| Device type (0x8F00) | 5648 (0x1610) |
| Sub type (0x8F01) | 10000 (0x2710) |
| Protocol version (0x8F02) | 3000 (0x0BB8) |
| HW versions | Display: 0x03E9 (1001), Control: 0x044C (1100), Power: 0x044C (1100) |
| IP address | 192.168.0.30:502 |
| Modbus slave ID | 1 |
| Scan tool | `tools/hs3_register_scanner.py` (pymodbus 3.15, FC03+FC04) |

---

## Executive Summary

- **37 out of 40 register blocks responded successfully** via FC03 (holding registers)
- The 3 failures were **EV Charger Block 1 (0x3024–0x30BA)**, which uses **FC04 (input registers)**, not FC03 — re-scanned with FC04 and all 152 registers responded successfully
- **All 24 existing H2 register blocks work on HS3** except `battery_data` (0xA000) which returns all zeros (confirms issue #186)
- **All HS3-exclusive blocks responded**: EV charger config, EMS remote, averaged values, extended meter
- **Issue #202 priority registers all verified**: BatCurr (0x406B/0x406C), avg SOC (0x51B8), scaling factors (0x51BE, 0x4209, 0x8F0D)
- **EV charger key registers identified** across 6 states (unplugged / idle / scheduled charge / surplus solar / standard charge / stopped):
  - `0x309D` = charger/plug state (1=unplugged, 2=scheduled wait, 3=charging, 4=surplus solar idle, 5=init idle, 6=paused)
  - `0x309F` = L1 charging current (x0.1A) — confirmed at 4.0A and 11.3A
  - `0x30A5` = total charge power (W) — confirmed at 878W, 1047W, and 2730W
  - `0x30A6` = charge mode enum (0=off, 1=active charge, 2=scheduled waiting, 7=AI mode)
  - `0x30A8` = session energy (Wh) during charging
  - `0x309C` = charge strategy read-back (mirrors `0x4B12`)
  - `0x4B12` = charge strategy selector — **writable** (0=off, 1=standard, 2=scheduled, 3=surplus solar)
  - `0x4B15` = max charge power (W) — **writable** (user-configured power cap)
  - `0x4B24` = dynamic power limit (W) — **writable** (EMS adjusts during smart charging modes)
  - `0x4B43` = min charging power toggle — **writable** (0=off, 4=on, surplus solar mode only)
- **Full schedule write control verified**: 4 plan slots at `0x4B20–0x4B33`, 5 registers per plan (start time, end time, day bitmask + mode, reserved, charge power)
- **Start/stop control**: writing `0x4B12=1` starts standard charging, writing `0x4B12=0` stops charging (charger ramps up in ~5s)

### Critical Finding: EV Charger Block 1 requires FC04

The EV charger real-time data registers at **0x3024–0x30BA** are **input registers**, not holding registers. They must be read with **function code 04** (`read_input_registers`), not FC03 (`read_holding_registers`). This is unlike all other register blocks in the integration, which use FC03.

The EV charger config/settings at **0x4B00–0x4B47** use FC03 as expected.

---

## 1. Existing H2 Register Blocks (Verification)

All 24 existing register blocks respond on the HS3 with live data, confirming backward compatibility.

| Block | Address | Count | Status | Non-zero |
|-------|---------|-------|--------|----------|
| device_info | `0x8F00` | 29 | OK | 28/29 |
| realtime_data | `0x4004` | 19 | OK | 8/19 |
| inverter_settings | `0x4023` | 14 | OK | 13/14 |
| grid_phase_r | `0x4031` | 7 | OK | 7/7 |
| grid_phase_s | `0x4038` | 7 | OK | 7/7 |
| grid_phase_t | `0x403F` | 7 | OK | 7/7 |
| inv_phase_r | `0x4046` | 5 | OK | 5/5 |
| inv_phase_s | `0x404B` | 5 | OK | 5/5 |
| inv_phase_t | `0x4050` | 5 | OK | 5/5 |
| offgrid_r | `0x4055` | 6 | OK | 2/6 |
| offgrid_s | `0x405B` | 6 | OK | 2/6 |
| offgrid_t | `0x4061` | 6 | OK | 5/6 |
| pv_battery_1 | `0x406E` | 15 | OK | 14/15 |
| side_net | `0x408D` | 8 | OK | 8/8 |
| power_directions | `0x4095` | 25 | OK | 14/25 |
| energy_totals_1 | `0x40BF` | 32 | OK | 18/32 |
| energy_totals_2 | `0x40DF` | 32 | OK | 21/32 |
| energy_totals_3 | `0x4137` | 30 | OK | 10/30 |
| energy_totals_4 | `0x4155` | 34 | OK | 26/34 |
| charge_schedule | `0x3604` | 23 | OK | 7/23 |
| discharge_schedule | `0x361B` | 21 | OK | 5/21 |
| passive_battery | `0x3636` | 43 | OK | 33/43 |
| battery_data | `0xA000` | 56 | OK | **0/56** |
| meter_a | `0xA03D` | 18 | OK | 18/18 |

### Notable: battery_data (0xA000) returns all zeros

All 56 registers in the battery data block returned zero. This confirms the behavior reported in issue #186: on HS3, registers like battery voltage, current, temperature, and cycle count are not populated at this address range. Only battery SOC is available via `0x406F` (in the `pv_battery_1` block, which works fine — value 5275 = 52.75% at time of scan).

---

## 2. EV Charger Registers

### Block 1: Real-Time Data (0x3024–0x30BA) — FC04 Input Registers

152 registers scanned across three charger states: idle (plugged in, not charging), unplugged, and actively charging.

#### Device identification strings (ASCII-encoded, 2 chars per register)

Static across all states — these are device identity constants.

| Registers | Decoded String | Meaning |
|-----------|---------------|---------|
| `0x3024–0x302C` | `E2AS113A2506E00005` | EV charger serial number |
| `0x3034–0x3039` | `CU2-11K-T-I` | EV charger model (11kW, T=three-phase, I=integrated?) |
| `0x303C–0x3043` | `1.6.78` / `1.0.02` | Firmware versions (main / secondary) |

#### 3-State Register Comparison

The table below shows all registers that had non-zero values in any state, with the value from each state. Registers marked "NEW" only appear during charging.

| Address | Unplugged | Idle (plugged) | Charging | Interpretation | Confidence |
|---------|-----------|---------------|----------|----------------|------------|
| `0x3046` | 3 | 3 | 3 | Charger mode (constant, 3 = normal mode?) | Medium |
| `0x3047` | 4140 | 4140 | 4140 | Unknown constant (414.0?) | Low |
| `0x3049` | 11000 | 11000 | 11000 | Max rated power: 11000W = 11kW | High |
| `0x304A` | 1 | 1 | 1 | Charger online / enabled flag | Medium |
| `0x309C` | 2 | 2 | 2 | Charge strategy read-back (mirrors `0x4B12`: 0=off, 1=std, 2=sched, 3=surplus) | High |
| **`0x309D`** | **1** | **5** | **3** | **Charger/plug state** (see state table below) | **High** |
| `0x309E` | 2374 | 2367 | 2371 | Grid voltage L1 (x0.1 = ~237V) | High |
| **`0x309F`** | **0** | **0** | **40** | **L1 charging current (x0.1 = 4.0A)** — only during charging | **High** |
| `0x30A0` | 2379 | 2388 | 2393 | Grid voltage L2 (x0.1 = ~239V) | High |
| **`0x30A1`** | **0** | **0** | **1** | **L2 current or flag** — only during charging | Medium |
| `0x30A2` | 2358 | 2350 | 2374 | Grid voltage L3 (x0.1 = ~237V) | High |
| **`0x30A3`** | **0** | **0** | **1** | **L3 current or flag** — only during charging | Medium |
| **`0x30A5`** | **0** | **0** | **1047** | **Total charge power (W)** — only during charging | **High** |
| **`0x30A6`** | **0** | **0** | **1** | **Charging active flag** — only during charging | Medium |
| `0x30A8` | 4299 | 4299 | 22→31 | Dual-purpose: idle=total kWh (42.99?); charging=session energy (Wh) | Medium |
| `0x30A9` | 32 | 32 | 32 | Max current capacity: 32A | High |
| `0x30AA` | 64520 | 64520 | 64520 | Constant signed -1016 — internal reference or offset | Low |
| `0x30AF` | 1215 | 915 | 603 | Fluctuates across all states — grid metric? | Low |
| `0x30B0` | **0** | 156 | 106 | **Connection-related counter** — zero when unplugged, non-zero when connected. Possibly session duration in minutes | Medium |
| `0x30B6` | 1 | 1 | 1 | Charger enabled flag | Medium |
| `0x30B7` | 94 | 94 | 64 | Drops during charging — available power headroom? duty cycle? | Low |
| `0x30B8` | 23754 | 23754 | 23754 | Energy counter high word (32-bit pair with 0x30B9) | Medium |
| `0x30B9` | 7338 | 7338 | 28927→29040 | Energy counter low word — incrementing during charge | Medium |
| `0x30BA` | 23754 | 23754 | 23754 | Energy counter high word (32-bit pair with 0x30BB) | Medium |
| `0x30BB` | 16150 | 11121 | 29016→29040 | Energy counter low word — incrementing continuously | Medium |

#### Charger State Register (0x309D)

| Value | Observed State | IEC 61851 Equivalent |
|-------|---------------|---------------------|
| 1 | Unplugged / no cable | State A (not connected) |
| 2 | Connected, scheduled mode waiting for time window | State B (connected, not charging) |
| 3 | Actively charging (any mode: scheduled, standard, surplus solar) | State C (charging) |
| 4 | Connected, surplus solar mode idle (waiting for sufficient surplus) | State B variant (connected, waiting for solar) |
| 5 | Connected idle — transitional state seen during mode switches (~5s before charging starts) | State B (connected, initializing) |
| 6 | Paused — stopped/AI mode idle, or manually paused | State B variant (connected, paused) |

All 6 states verified across mode switching and start/stop operations.

#### Charge Strategy Register (0x4B12 write / 0x309C read-back) — WRITABLE

Write-verified via Modbus FC06. FC04 read-back at `0x309C` mirrors the value with ~2-3s propagation delay.

| 0x4B12 | 0x309C | Mode | Behavior |
|--------|--------|------|----------|
| 0 | 0 | Off / No charging | Charger paused; used as "stop" command |
| 1 | 1 | Standard | Charge immediately at configured power (`0x4B15`); charger starts in ~5s |
| 2 | 2 | Scheduled | Charge during configured time windows (`0x4B20–0x4B33`) |
| 3 | 3 | Surplus Solar | Charge from excess solar production; respects min power toggle (`0x4B43`) |
| ? | ? | AI / Smart | Not captured — activation failed on test unit; value unknown |

#### Charge Mode Register (0x30A6)

| Value | Meaning |
|-------|---------|
| 0 | Not charging (unplugged or idle in standard mode) |
| 1 | Actively charging (any strategy) |
| 2 | Scheduled mode — waiting for time window (outside schedule) |
| 7 | AI mode — waiting for solar/smart decision |

#### Charging Power Verification

During active charging, the register values are internally consistent:

- L1 voltage: `0x309E` = 2370 → 237.0V (x0.1)
- L1 current: `0x309F` = 40 → 4.0A (x0.1)
- Expected power: 237.0V × 4.0A = 948W
- Reported power: `0x30A5` = 1047W (difference attributable to power factor and measurement timing)

The charge was running on **single-phase** at ~4A/~1kW. L2 and L3 (`0x30A1`, `0x30A3`) showed value 1, which may be a flag rather than a current reading — needs verification during 3-phase charging.

#### Session Energy Register (0x30A8)

During charging, `0x30A8` appears to track session energy in Wh. Two samples 5 seconds apart at ~1047W:

| Time | Register Value | Expected (at 1047W) |
|------|---------------|---------------------|
| t=0 | 22 Wh | 22.0 Wh |
| t+5s | 28 Wh | 23.5 Wh |
| t+10s | 31 Wh | 24.9 Wh |

The increment rate is roughly consistent with the measured power. When idle, this register showed 4299 — possibly a different metric (total kWh at x0.01 = 42.99 kWh?) or the register changes meaning based on charger state.

#### AI Mode State (4th scan: plugged in, AI/smart charging)

A fourth scan was taken with the charger in "AI mode" — the EMS decides when and how much to charge based on solar availability.

**Block 1 changes (FC04 input registers):**

| Address | Previous States | AI Mode | Interpretation |
|---------|----------------|---------|----------------|
| `0x309C` | 2 (all prior) | **0** | Cleared in AI mode |
| `0x309D` | 1/5/3 | **6** | **New state: AI mode / EMS-controlled pause** |
| `0x30A6` | 0/0/1 | **7** | **Charge mode enum** (not a boolean): 0=off, 1=charging, 2=sched waiting, 7=AI mode |
| `0x30A8` | 4299/4299/22→31 | **121** | Session energy: 121 Wh accumulated from earlier charge burst |
| `0x30B0` | 0/156/106 | **0** | Zero — charger paused |
| `0x30B6` | 1 (all prior) | **0** | Charging paused by AI — was always 1 before |

**Block 2 changes (FC03 holding registers) — AI mode rewrites config:**

| Address | Idle/Charging | AI Mode | Interpretation |
|---------|-------------|---------|----------------|
| `0x4B00` | 25208/43160 | **46576** | Third distinct value — encodes runtime state |
| `0x4B02` | 261/263 | **265** | Incrementing counter (+2 per state change) |
| `0x4B12` | 2 | **0** | **Charge strategy: 0 = AI/automatic** (was 2 = scheduled?) |
| `0x4B20` | 2304 (09:00) | **0** | Schedule slot 1 start: cleared by AI mode |
| `0x4B21` | 4096/4352 | **0** | Schedule slot 1 end: cleared |
| `0x4B22` | 32513 | **3** | Day mask changed — AI overrides schedule |
| `0x4B24` | 6700/4600 | **0** | **Power limit: 0 = no fixed limit, AI controls dynamically** |
| `0x4B26–0x4B29` | had values | **0** | All remaining schedule slots cleared |

**Key insight:** In AI mode, the EMS clears the fixed schedules and power limits, taking full dynamic control. Register `0x4B12` appears to be the **charge strategy selector**: 0=AI, 2=scheduled. Register `0x30A6` is a **charge mode enum** (not boolean): 0=off, 1=active charge, 7=AI mode.

#### Standard Charging Mode (5th scan: immediate charge, no schedule)

A fifth scan was taken in "standard" mode — charge immediately at available power without schedule or AI constraints. The charger was drawing **2730W at 11.3A single-phase**.

**Block 1 (FC04) — higher power confirms register meanings:**

| Address | AI Mode | Std Charge | Interpretation |
|---------|---------|-----------|----------------|
| `0x309C` | 0 | **1** | **Charge strategy echo**: 0=AI, 1=standard, 2=scheduled (mirrors `0x4B12`) |
| `0x309D` | 6 | **3** | Charging (same as scheduled charging state) |
| `0x309F` | 0 | **113** | L1 current: **11.3A** (x0.1) — verified: 233.9V × 11.3A ≈ 2643W ≈ 2730W reported |
| `0x30A5` | 0 | **2730** | Charge power: **2730W** |
| `0x30A6` | 7 | **1** | Active charge (1), not AI (7) |
| `0x30A8` | 121 | **39** | New session energy: 39 Wh |
| `0x30B0` | 0 | **266** | Connection duration/counter — highest value yet |
| `0x30B7` | 64 | **160** | Increases with power — possibly available capacity headroom or PWM duty? |

**Block 2 (FC03) — charge strategy register confirmed:**

| Address | Scheduled | AI Mode | Standard | Interpretation |
|---------|----------|---------|----------|----------------|
| `0x4B12` | 2 | 0 | **1** | **Charge strategy: 0=AI, 1=standard, 2=scheduled** |
| `0x4B20–0x4B29` | schedules set | 0 | **0** | No schedules in standard or AI mode |
| `0x4B24` | 6700→4600 | 0 | **0** | No power limit in standard mode (charges at max available) |
| `0x4B02` | 263 | 265 | **266** | Counter incremented again |

#### Gap analysis

The ranges `0x3056–0x3087` (50 registers) and `0x3088–0x309B` (20 registers) remained **all zeros across all five states** (unplugged, idle, scheduled charge, AI mode, standard charge). These may require 3-phase charging to populate, or may be reserved/unused on this firmware version.

### Block 2: Configuration/Settings (0x4B00–0x4B47) — FC03 Holding Registers

72 registers scanned, 22 non-zero when idle. Contrary to initial expectations, **4 registers changed during active charging** — this block is not purely static configuration.

| Address | Idle | Charging | Hex (charging) | Interpretation | Confidence |
|---------|------|----------|----------------|----------------|------------|
| `0x4B00` | 25208 | **43160** | `0xA898` | Not static — runtime status mixed in? Was ASCII "bx" when idle | Low |
| `0x4B01` | 80 | 80 | `0x0050` | Max current setting | Low |
| `0x4B02` | 261 | **263** | `0x0107` | Version or counter — incremented from 0x0105 to 0x0107 | Low |
| `0x4B03` | 1001 | 1001 | `0x03E9` | Configuration ID or serial suffix | Low |
| `0x4B04` | 1 | 1 | `0x0001` | Boolean: enabled | Medium |
| `0x4B05` | 1 | 1 | `0x0001` | Boolean: enabled | Medium |
| `0x4B06` | 4 | 4 | `0x0004` | Charge mode (4 = solar priority? smart?) | Low |
| `0x4B07` | 1 | 1 | `0x0001` | Boolean: enabled | Medium |
| `0x4B08` | 5 | 5 | `0x0005` | Minimum charge current: 5A (OCPP standard min for EU) | High |
| `0x4B09` | 1 | 1 | `0x0001` | Boolean: enabled | Medium |
| `0x4B0A` | 1 | 1 | `0x0001` | Boolean: enabled | Medium |
| `0x4B12` | 2 | 2 | `0x0002` | Charge mode / EV charge strategy | Low |
| `0x4B13` | 3 | 3 | `0x0003` | Phase configuration: 3-phase | High |
| `0x4B15` | 6700 | 6700 | `0x1A2C` | Max charge power: 6700W = 6.7kW | High |
| `0x4B20` | 2304 | 2304 | `0x0900` | Schedule slot 1 start: 09:00 | High |
| `0x4B21` | 4096 | **4352** | `0x1100` | Schedule slot 1 end: was 16:00, now **17:00** | High |
| `0x4B22` | 32513 | 32513 | `0x7F01` | Day mask + power: 0x7F=all days, 0x01=1% | High |
| `0x4B24` | 6700 | **4600** | `0x11F8` | **Dynamic power limit: dropped from 6.7kW to 4.6kW** during charge | **High** |
| `0x4B26` | 1536 | 1536 | `0x0600` | Schedule slot 2 start: 06:00 | High |
| `0x4B27` | 7937 | 7937 | `0x1F01` | Day mask + power: 0x1F=Mon-Fri, 0x01=1% | High |
| `0x4B29` | 6700 | 6700 | `0x1A2C` | Max charge power (slot 3?) | High |
| `0x4B43` | 4 | 4 | `0x0004` | **Min charging power toggle** (0=off, 4=on) — surplus solar mode | **High** |

#### Dynamic behavior during charging

Four registers changed during active charging:

| Address | Idle → Charging | Interpretation |
|---------|----------------|----------------|
| `0x4B00` | 25208 → 43160 | Runtime status — value changes significantly, no longer ASCII |
| `0x4B02` | 261 → 263 | Counter or minor version increment |
| `0x4B21` | 4096 → 4352 | Schedule end time changed from 16:00 to 17:00 (dynamic?) |
| **`0x4B24`** | **6700 → 4600** | **Active power limit reduced from 6.7kW to 4.6kW** — likely solar-aware dynamic adjustment by the EMS |

The `0x4B24` change is particularly notable: it suggests the inverter's energy management system dynamically adjusts the EV charger's power limit based on available solar/grid capacity. If this register is writable, it could be used to control charging power from Home Assistant.

#### Schedule Format (verified via write tests, 2026-10-07)

4 plan slots, 5 registers each. Verified by creating/modifying/deleting plans via Modbus and confirming in the SAJ app.

| Slot | Base Address | Registers |
|------|-------------|-----------|
| Plan 1 | `0x4B20` | `0x4B20–0x4B24` |
| Plan 2 | `0x4B25` | `0x4B25–0x4B29` |
| Plan 3 | `0x4B2A` | `0x4B2A–0x4B2E` |
| Plan 4 | `0x4B2F` | `0x4B2F–0x4B33` |

Each plan slot (5 registers):

| Offset | Field | Encoding | Example |
|--------|-------|----------|---------|
| +0 | Start time | `hour << 8 \| minute` | `0x0A00` = 10:00 |
| +1 | End time | `hour << 8 \| minute` | `0x0F0F` = 15:15 |
| +2 | Config | hi = day bitmask (bit0=Mon...bit6=Sun), lo = charge mode (1=standard) | `0x7F01` = Mon-Sun, standard |
| +3 | Reserved | Always 0 | |
| +4 | Charge power | Watts | 6700 |

Day bitmask examples:
- `0x1F` (31) = Mon–Fri
- `0x7F` (127) = Mon–Sun
- `0x05` (5) = Mon+Wed
- `0x48` (72) = Thu+Sun

Verified operations: create plan, modify end time, modify power, delete plan (write all 5 registers to 0). The SAJ app reflects changes within seconds.

Note: Registers `0x4B16–0x4B1F` (slots A and B, 10 registers before Plan 1) were always zero in all tests. They may be reserved for additional plan types or firmware-level schedules.

#### Write Control Summary (verified 2026-10-07)

All registers below were verified writable via Modbus FC06 (write single register) and confirmed via both register read-back and SAJ app observation.

| Register | Field | Values | Write-verified |
|----------|-------|--------|---------------|
| `0x4B12` | Charge strategy | 0=off, 1=standard, 2=scheduled, 3=surplus solar | Yes — mode switch + start/stop |
| `0x4B15` | Max charge power | Watts (e.g., 4140, 6700) | Yes — app reflected change |
| `0x4B24` | Dynamic power limit | Watts | Yes — read-back confirmed |
| `0x4B20–0x4B33` | Schedule plans (4×5 regs) | See format above | Yes — create/modify/delete |
| `0x4B43` | Min charging power toggle | 0=off, 4=on (surplus solar mode) | Yes — diff-verified |

**Start/stop charging:**
- Write `0x4B12 = 1` → charger transitions: state 5 (init) → state 3 (charging) in ~5 seconds
- Write `0x4B12 = 0` → charger transitions to state 6 (paused), power drops to 0W immediately
- The SAJ app "stop charging" button also writes `0x4B12 = 0`

**Propagation delay:** FC03 (holding registers) updates immediately after write. FC04 (input registers) read-back at `0x309C` mirrors the new value with ~2-3 second delay.

---

## 3. Issue #202 Priority Register Verification

### Battery Current Area (0x4067–0x407C)

18 of 22 registers respond with data:

| Address | Value | Signed | Known Mapping |
|---------|-------|--------|---------------|
| `0x4067` | 6685 | 6685 | — |
| `0x4069` | 4597 | 4597 | Battery voltage (459.7V at x0.1?) |
| `0x406A` | 64229 | -1307 | Battery current: -13.07A (x0.01, signed) — confirmed by stanus |
| `0x406B` | 0 | 0 | **BatCurr1 — returns 0 (not -1/0xFFFF)** |
| `0x406C` | 0 | 0 | **BatCurr2 — returns 0 (not -1/0xFFFF)** |
| `0x406D` | 59528 | -6008 | — |
| `0x406E` | 270 | 270 | Battery temperature (27.0°C at x0.1) |
| `0x406F` | 5275 | 5275 | Battery SOC: 52.75% (confirmed working) |
| `0x4071` | 2511 | 2511 | PV1 voltage: 251.1V (x0.1) |
| `0x4072` | 1299 | 1299 | PV1 current: 12.99A (x0.1) |
| `0x4073` | 3258 | 3258 | PV1 power: 3258W |
| `0x4074` | 2493 | 2493 | PV2 voltage: 249.3V (x0.1) |
| `0x4075` | 1311 | 1311 | PV2 current: 13.11A (x0.1) |
| `0x4076` | 3260 | 3260 | PV2 power: 3260W |
| `0x4077` | 65535 | -1 | PV3 voltage: N/A (0xFFFF = not connected) |
| `0x4078` | 65535 | -1 | PV3 current: N/A |
| `0x4079` | 65535 | -1 | PV3 power: N/A |
| `0x407A–0x407C` | 65535 | -1 | PV4: N/A (not connected) |

**Result:** `0x406B` and `0x406C` (BatCurr1/BatCurr2) return 0, not an error. They may need battery discharge/charge activity to show non-zero values, or the HS3 may report battery current elsewhere.

### Average SOC (0x51B8)

| Address | Value | Interpretation |
|---------|-------|---------------|
| `0x51B8` | 5228 | Average SOC: 52.28% (x0.01 scale, consistent with 0x406F = 52.75%) |

**Result:** Confirmed working. Value is plausible.

### Scaling Factors

| Address | Value | Interpretation |
|---------|-------|---------------|
| `0x51BE` | 270 | Matches battery temp at `0x406E` (27.0°C x0.1) — averaged temp? |
| `0x4209` | 52 | Could be a scaling divisor, or simplified SOC (52%) |
| `0x8F0D` | 12592 | ASCII "10" — part of serial/product code string, not a numeric scale |

---

## 4. Other HS3-Exclusive Blocks

### EMS Remote Control (0x8400–0x8405, 0x840F–0x8412)

| Address | Value | Notes |
|---------|-------|-------|
| `0x8400` | 0 | — |
| `0x8401` | 300 | Power setting? (300W?) |
| `0x8402` | 0 | — |
| `0x8403` | 200 | Power setting? (200W?) |
| `0x8404` | 200 | Power setting? (200W?) |
| `0x8405` | 0 | — |
| `0x840F` | 10000 | Max power? (10000W = 10kW = rated power) |
| `0x8410` | 10000 | Repeated |
| `0x8411` | 0 | — |
| `0x8412` | 65535 | 0xFFFF (not set / disabled) |

### Averaged Values (0x513E–0x51BE)

89 of 129 registers are non-zero. This block appears to contain averaged measurements across all three phases. The repeating pattern with ~6 registers per group suggests:

- Groups of per-phase averaged data (voltage ~2350–2380 = 235.0–238.0V at x0.1)
- Frequency values (~4997–4998 = 49.97–49.98 Hz at x0.001)
- Current/power values (small positive numbers = current in x0.1A)
- Some registers show -1 (0xFFFF) indicating unused/not-applicable slots

### Extended Meter (0xA03C–0xA076)

25 of 59 registers are non-zero. The first register `0xA03C` = 1 (meter present flag?). This block overlaps with the existing `meter_a` block at `0xA03D` and extends it with additional data through `0xA076`.

The existing meter data (`0xA03D–0xA04E`) is intact. The extension adds registers at `0xA06C–0xA071` which contain negative values — possibly reverse power flow or accumulated export energy.

---

## 5. Raw Data Files

The following files contain the complete register dumps:

| File | Contents |
|------|----------|
| `hs3_scan_all_20261004_113636.csv` | Full scan — all 40 blocks, FC03 only (EV block 1 shows as ERROR) |
| `ev_charger_block1_fc04.csv` | EV charger block 1 (0x3024–0x30BB), FC04 input registers (idle) |
| `ev_unplugged_20261004_130903.csv` | EV charger blocks — unplugged state |
| `ev_charging_20261004_163654.csv` | EV charger blocks — actively charging state |
| AI mode scan | Captured in-memory during session (register values in report above) |
| `hs3_scan_all_20261004_113636.md` | Auto-generated summary |

---

## 6. Open Questions / TODO

- [x] ~~Re-scan EV charger block 1 while actively charging~~ — **Done.** Power (`0x30A5`), current (`0x309F`), session energy (`0x30A8`), and state (`0x309D`) identified.
- [ ] **Test 3-phase charging** — current scan was single-phase at ~4A. Need to verify `0x30A1`/`0x30A3` carry real current values during 3-phase charging, and whether the zero range `0x3056–0x3087` populates.
- [ ] **Determine if 0x4B24 (power limit) is writable** — it changed dynamically during charging (6700→4600), suggesting the EMS adjusts it. If writable via FC06/FC16, this is the key register for controlling charge power from HA.
- [ ] **Test writing to 0x4B00 config registers** — could enable controlling charge mode, current limits, and scheduling from HA. Start with a safe read-back test on non-critical registers.
- [ ] **Clarify battery_data (0xA000) all-zeros** — is this a known HS3 limitation? Does HS3 report battery data via a different register block?
- [ ] **Map the averaged values block (0x513E–0x51BE)** — determine which averaged metric each register corresponds to.
- [ ] **Verify EMS remote control registers** — are 0x8400–0x8412 writable for external energy management?
- [ ] **Observe remaining charger states** — capture values for state 2 (preparing?) and 4 (charging complete?) in `0x309D`, and confirm full state machine.

---

## Methodology

1. Stopped Home Assistant SAJ integration (HS3 allows only one Modbus TCP connection)
2. Scanned all register blocks using `tools/hs3_register_scanner.py` with pymodbus 3.15
3. Initial scan used FC03 (holding registers) for all blocks
4. Discovered EV charger block 1 (0x3024–0x30BA) returns exception code 48 on FC03
5. Re-scanned block 1 with FC04 (input registers) — all registers responded
6. Decoded ASCII-encoded fields to identify charger model, serial, and firmware
7. Cross-referenced voltage readings with known grid voltage (~230V) to validate x0.1 scaling

**Scanner tool:** Available at `tools/hs3_register_scanner.py` in the repo. Now updated to automatically use FC04 for the 0x3024 block. Other HS3 owners can run:

```bash
pip install pymodbus
python3 tools/hs3_register_scanner.py --host <YOUR_HS3_IP> --scan all --output-dir ./scan_results
```
