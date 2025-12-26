# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paternologia is a web application for managing MIDI device configurations for songs. The main controller is **PACER** (up to 6 buttons, each can execute up to 6 actions).

## Commands

```bash
# Development server (hot reload)
uv run fastapi dev src/paternologia/main.py

# Production server
uv run fastapi run src/paternologia/main.py

# Run all tests
uv run pytest

# Run single test file
uv run pytest tests/test_models.py -v

# Run specific test
uv run pytest tests/test_models.py::TestDevice::test_device_creation_minimal -v

# Sync dependencies
uv sync
```

## Architecture

### Data Flow
```
YAML files (data/) → Storage layer → Pydantic models → FastAPI routers → Jinja2 templates (HTMX)
```

### Key Components

**Models** (`src/paternologia/models.py`):
- `Device` - MIDI device with supported action types (preset, pattern, cc)
- `Action` - Single MIDI action with device, type, value, cc, label
- `PacerButton` - Button with name and up to 6 actions
- `Song` - Complete song with metadata and PACER buttons

**Storage** (`src/paternologia/storage.py`):
- YAML-based persistence in `data/devices.yaml` and `data/songs/*.yaml`
- Song ID = filename (e.g., `w-ciszy.yaml` → song id `w-ciszy`)

**Routers**:
- `songs.py` - CRUD for songs, HTMX partials for dynamic forms
- `devices.py` - Device listing and JSON API

**Templates**:
- HTMX for interactivity without JavaScript SPA
- TailwindCSS via CDN for styling
- Partials in `templates/partials/` for reusable components

### Constraints
- Maximum 6 PACER buttons per song
- Maximum 6 actions per button
- Action types: `preset`, `pattern`, `cc`

## Data Format

Songs are stored as YAML with this structure:
```yaml
song:
  id: song-id
  name: "Display Name"
  author: "Author"
  created: 2024-12-14
  notes: "Optional notes"
pacer:
  - name: "Button Name"
    actions:
      - device: boss
        type: preset
        value: 1
        label: "Optional"
```

## Testing

Three test levels:
- `test_models.py` - Pydantic model validation
- `test_storage.py` - YAML persistence
- `test_api.py` + `test_e2e.py` - FastAPI endpoints and user workflows

Tests use temporary directories via pytest fixtures to isolate storage.

## References

### pacer-editor (git submodule)

Located at `workspace/pacer-editor/` - reference implementation for Nektar Pacer protocol:
- `src/pacer/constants.js` - Protocol constants (control IDs, message types, LED colors)
- `src/pacer/sysex.js` - SysEx message building, checksum algorithm
- `sysex.md`, `data_structure.md` - Protocol documentation

**Usage:**
- Reference source of truth for protocol implementation
- Visual verification tool (drag .syx files to http://localhost:3000)
- Optional: `cd workspace/pacer-editor && NODE_OPTIONS=--openssl-legacy-provider yarn start`

**Note:** Web MIDI doesn't work on Ubuntu/snap - use `amidi` for actual device communication.

## Pacer SysEx Protocol - Critical Information

### Preset Indices (TARGET_PRESET = 0x01)
According to `pacer-editor/dumps/README.md`:
- idx 0x00 = Current (RAM only, changes visible immediately, dots blink)
- idx 0x01 = A1, 0x02 = A2, ..., 0x06 = A6
- idx 0x07 = B1, ..., 0x0C = B6
- idx 0x0D = C1, ..., 0x12 = C6
- idx 0x13 = D1, ..., 0x18 = D6

Formula: `preset_index = (bank * 6) + col` where bank=0-3 (A-D), col=1-6

### SysEx Export - How It Works
Export writes preset data directly to EEPROM slot (e.g., A1 = idx 0x01):
```bash
amidi -p hw:5,0,0 -s song_A1.syx
```

**After sending SysEx:**
- Data is saved to the slot (EEPROM)
- To see changes: switch presets on Pacer (UP/DOWN arrows)
- This is faster than manual save via Pacer's encoder

**Important:** Never write to multiple slots (e.g., A1 + Current) in single .syx file - this can brick Pacer!

### DANGEROUS COMMANDS - DO NOT SEND
From `workspace/pacer_programming/pacer-editor/dumps/README.md`:
```
01 05 00 01 1E 04   DOES NOT WORK. DO NOT SEND. NEED RESET AFTER.
```
**NEVER send TARGET_GLOBAL (0x05) with elm=0x1E (Current User Preset)** - this bricks the Pacer and requires factory reset!

### Factory Reset Procedure
If Pacer becomes unresponsive (can't switch presets):

**Exit FWUPD mode first** (if display shows "FWUPD"):
- Simply power off and power on normally (without holding any buttons)

**Factory Restore** (from User Guide page 21):
1. Power off Pacer
2. Hold **[Preset]** switch while powering on
3. Display shows "G CFG" - rotate **Data Encoder** until you see **"RESET"**
4. Press **Data Encoder** to confirm
5. Reset completes immediately

**Warning:** Backup presets before reset - all custom settings will be lost!

### Known Limitations
- Cannot remotely force Pacer to auto-reload preset after SysEx write
- After saving via SysEx, switch presets (UP/DOWN) to refresh display
- Preset D6 cannot be read alone (pacer-editor bug)
