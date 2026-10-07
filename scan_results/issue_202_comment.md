### HS3-10K-T2-W-PX — Full scan + write-control verification (3-phase, with EV charger)

**Device:** SAJ HS3-10K-T2-W-PX, Display V2.1.20, Master V2.1.30, HW 1001/1100/1100  
**EV Charger:** CU2-11K-T-I (11kW integrated), FW 1.6.78  
**Tool:** Custom pymodbus scanner ([`tools/hs3_register_scanner.py`](../tools/hs3_register_scanner.py))

#### Priority 1–3: Confirmed (aligns with @fvezzoli)

- `0x406B`/`0x406C`: both respond with 0, 22-register block read succeeds ✓
- `0x4069`=4597 (459.7V), `0x406A`=64229 (−13.07A ×0.01), `0x406D`=59528 (−6008W) — cross-check: 459.7V × 13.07A ≈ 6008W ✓
- `0x51B8`=5228 (52.28%), `0x51BE`=270 (27.0°C), `0x4209`=52 (integer % ×1) ✓
- `0x3636–0x3660` 43-register block: succeeds, `0x363A`=1000

#### 3-phase data: `0x4091–0x4094` NOT zero

Since @fvezzoli has a single-phase unit, these were all 0. On our 3-phase HS3-10K they respond:  
`0x4091`=2372 (237.2V), `0x4092`=124, `0x4093`=2381 (238.1V), `0x4094`=280

#### `0xA000` battery_data block: all 56 registers return 0

Confirms issue #186. SOC is only available via `0x406F` (worked fine, value=5275).

#### EV Charger registers — critical finding: Block 1 uses FC04

**EV Charger Block 1 (`0x3024–0x30BA`) responds to FC04 (input registers), NOT FC03.** FC03 returns exception code 48 for the entire range. Block 2 (`0x4B00–0x4B47`) uses FC03 as normal.

Scanned across 6 charger states (unplugged / idle / scheduled / surplus solar / standard charging / stopped):

| Register | FC | Description | Scale | Confidence |
|----------|-----|------------|-------|------------|
| `0x309D` | FC04 | Plug/charge state | 1=unplugged, 2=sched wait, 3=charging, 4=solar idle, 5=init idle, 6=paused | High |
| `0x309E` | FC04 | Voltage L1 | ×0.1 V | High |
| `0x309F` | FC04 | Current L1 | ×0.1 A (verified at 3.7A, 4.0A, and 11.3A) | High |
| `0x30A0` | FC04 | Voltage L2 | ×0.1 V | High |
| `0x30A2` | FC04 | Voltage L3 | ×0.1 V | High |
| `0x30A5` | FC04 | Total charge power | W (verified at 878W, 1047W, and 2730W) | High |
| `0x30A6` | FC04 | Charge mode | 0=off, 1=charging, 2=sched waiting | High |
| `0x30A8` | FC04 | Session energy | Wh (rate-verified against power) | Medium |
| `0x30A9` | FC04 | Max current capacity | A (constant 32-33) | High |
| `0x4B12` | FC03 | **Charge strategy (R/W)** | 0=off, 1=standard, 2=scheduled, 3=surplus solar | **High** |
| `0x4B15` | FC03 | **Max charge power (R/W)** | W (user-configured, e.g. 4140, 6700) | **High** |
| `0x4B24` | FC03 | **Dynamic power limit (R/W)** | W (EMS adjusts during smart modes) | **High** |
| `0x4B43` | FC03 | **Min power toggle (R/W)** | 0=off, 4=on (surplus solar only) | **High** |

#### NEW: Write Control Verified (2026-10-07)

All FC03 config registers are **writable via FC06** (write single register). Verified operations:

- **Start/stop charging**: write `0x4B12=1` (start standard) / `0x4B12=0` (stop). Charger ramps up in ~5s.
- **Mode switching**: Standard ↔ Scheduled ↔ Surplus Solar — confirmed via app.
- **Power control**: `0x4B15` (max power) and `0x4B24` (dynamic limit) both writable.
- **Schedule management**: 4 plan slots at `0x4B20–0x4B33`, 5 registers each:
  - +0: start time (`hour<<8|min`), +1: end time, +2: config (`hi=day_bitmask, lo=mode`), +3: reserved, +4: power (W)
  - Day bitmask: bit0=Mon...bit6=Sun (e.g., `0x1F`=Mon-Fri, `0x7F`=Mon-Sun)
  - Create, modify, delete plans all verified — SAJ app reflects changes within seconds.

**AI mode:** Strategy value unknown — activation failed on our unit (error in app). Value 0 appears to be "off/no charging" rather than AI. Needs verification from another HS3 owner with working AI mode.

Full report with per-register raw data across all 6 states: [HS3_REGISTER_REPORT.md](../scan_results/HS3_REGISTER_REPORT.md)  
CSV dumps: [`scan_results/`](../scan_results/)
