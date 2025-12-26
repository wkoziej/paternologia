# Problem: LED Colors and 6th Button PGBNK Bug

## Problem Statement

When exporting songs to Pacer .syx files:
1. **All 6 buttons light up** even when only 3-4 have defined actions
2. **6th button shows "PGBNK 005"** on LCD instead of configured action (or being empty)
3. **Empty buttons should have LED OFF** but they still glow

## Expected Behavior

- Only buttons WITH actions should have LED lit (BLUE active, AMBER inactive)
- Buttons WITHOUT actions should have LED OFF
- 6th button (SW6) should show its configured action OR be empty/dark

## What Was Tried

### 1. Added Control Mode (0x60)
- Hypothesis: Missing control mode causes old config to persist
- Implementation: Added `build_control_mode()` to sysex.py, sends mode=0 ("all steps in one shot")
- Result: **No change**

### 2. LED for All 6 Steps
- Hypothesis: Pacer needs LED config for all 6 steps, not just step 1
- Implementation: Changed `build_control_led()` to accept step_index, export LED for steps 1-6
- Result: **No change**

### 3. Fixed LED_OFF Value
- Hypothesis: LED_OFF should be 0x7F, not 0x00 (0x00 is Pink color)
- Evidence: pacer-editor `PresetsOverview.js:66-67` treats 127 (0x7F) as OFF
- Implementation: Changed `LED_OFF = 0x7F` in constants.py
- Result: **Not tested yet / No change reported**

## Current Export Structure

Each preset export contains (79 messages total):
1. Preset name (1 message)
2. For each of 6 stompswitches (SW1-SW6):
   - Control Mode (1 message)
   - Steps 1-6 configuration (6 messages)
   - LED steps 1-6 configuration (6 messages)

## Files for Analysis

### Generated SysEx files (not working):
- `workspace/w-ciszy_A1_v2.syx` - 3 buttons with actions
- `workspace/zen_A3_v2.syx` - 4 buttons with actions

### Reference files:
- `workspace/pacer_programming/pacer-editor/patches/factory/Pacer A1 factory.syx` - Factory preset

### Key source files:
- `src/paternologia/pacer/export.py` - Main export logic
- `src/paternologia/pacer/sysex.py` - SysEx message builders
- `src/paternologia/pacer/constants.py` - Protocol constants
- `workspace/pacer_programming/pacer-editor/src/pacer/sysex.js` - Reference implementation

## Hex Dump Comparison

### Factory A1 (working) - SW1 LED:
```
0d 40 01 00 00 41 01 7f 00 42 01 7f 00 43 01 00
```
- All LED colors = 0x7F (OFF as default)

### Our export - SW6 LED (empty button):
```
12 40 01 00 00 41 01 7f 00 42 01 7f 00 43 01 00
```
- LED colors = 0x7F (OFF) - **matches factory format**

### Our export - SW1 LED (button with actions):
```
0d 40 01 00 00 41 01 11 00 42 01 07 00 43 01 00
```
- Active = 0x11 (BLUE), Inactive = 0x07 (AMBER)

## Possible Causes Still to Investigate

1. **Order of messages** - Maybe Pacer expects different order?
2. **Missing element** - Factory might send additional data we're not aware of
3. **Checksum issues** - Though messages parse correctly in pacer-editor
4. **Step Active flag** - Maybe empty steps need `active=True` not `active=False`?
5. **EEPROM vs RAM** - Writing to preset slot (A1=0x01) should work, but maybe need to also write to Current (0x00)?

## Commands to Test

```bash
# Send to Pacer
amidi -p hw:5,0,0 -s workspace/w-ciszy_A1_v2.syx

# Hex dump for analysis
xxd workspace/w-ciszy_A1_v2.syx | head -50

# Compare with factory
xxd "workspace/pacer_programming/pacer-editor/patches/factory/Pacer A1 factory.syx" | head -50
```

## YAML Source Files

Songs with pacer configuration:
- `data/songs/w-ciszy.yaml` - 4 buttons defined
- `data/songs/zen.yaml` - 6 buttons defined

## Pacer-Editor Reference

The pacer-editor (JavaScript) is the source of truth for the protocol:
- `workspace/pacer_programming/pacer-editor/src/pacer/sysex.js` - Message building
- `workspace/pacer_programming/pacer-editor/src/pacer/constants.js` - All constants
- `workspace/pacer_programming/pacer-editor/dump_format.md` - Protocol docs
- `workspace/pacer_programming/pacer-editor/dumps/README.md` - Additional protocol info

## Key Protocol Details

- Manufacturer ID: `00 01 77`
- Device ID: `7F`
- CMD_SET: `01`
- TARGET_PRESET: `01`
- Preset indices: A1=0x01, A2=0x02, ..., A6=0x06, B1=0x07, ...
- Stompswitch IDs: SW1=0x0D, SW2=0x0E, ..., SW6=0x12
- Control Mode element: 0x60
- LED elements per step: 0x40-0x43 (step1), 0x44-0x47 (step2), etc.
- MSG_CTRL_OFF: 0x61
- LED_OFF: 0x7F (NOT 0x00!)
