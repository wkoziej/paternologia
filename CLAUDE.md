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
- `Song` - Complete song with metadata, device settings, and PACER buttons

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
devices:
  boss:
    preset: 1
    preset_name: "Preset Name"
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
