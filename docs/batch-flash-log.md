# Batch Flash Log — CW3D Arc Reactor
# STORY-003: Batch Flash & Test

## Firmware Reference

| File | MD5 |
|---|---|
| `adafruit-circuitpython-makergo_esp32c3_supermini-en_US-10.1.4.bin` | `b579130c38921cbfe2ddc7822f914dc4` |
| `src/code.py` | `f2861452148cccde0ecfc5ea1ee4c164` |
| `neopixel.mpy` (bundle 10.x-mpy-20260401) | — |

Flash command: `bash scripts/flash.sh`

---

## Board Log

| Board # | Firmware Flashed | CIRCUITPY Mounted | Files Copied | Power-On Test | Soak Test (2 min) | Notes | Disposition |
|---|---|---|---|---|---|---|---|
| 01 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 02 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 03 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 04 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 05 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 06 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 07 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 08 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 09 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 10 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | Kit bag |
| 11 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | **Spare 1** |
| 12 | ☐ / ☐ double | ☐ | ☐ | ☐ PASS / ☐ FAIL | ☐ PASS / ☐ FAIL | | **Spare 2** |

---

## Summary

- Boards flashed: — / 12
- Boards passed: — / 12
- Double-flashes required: —
- Hardware failures: —
- Replacements made: —

---

## Edge Case Notes

**Board fails to flash:** Re-run `bash scripts/flash.sh`. Check USB cable is data-capable.
**Animation missing after flash:** Verify board booted (tap RESET without BOOT after flashing).
**Dark pixel(s):** Hardware fault — set aside, use spare.
**Freeze during soak:** Do not ship — set aside, use spare.
