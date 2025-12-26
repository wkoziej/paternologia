# ABOUTME: Specyfikacja eksportu .syx z Paternologii (Faza 2 - zwięzła wersja)
# ABOUTME: Protokół SysEx, moduł pacer/, API, testy - gotowe do implementacji

# Eksport .syx z Paternologii

## Cel

Generator plików `.syx` (MIDI SysEx) dla Nektar Pacer:
- `Song` → `.syx` → wgranie przez `amidi` lub podgląd w `pacer-editor`

## Protokół SysEx Nektar Pacer

### Struktura ramki

```
F0                    # SysEx Start
00 01 77              # Manufacturer ID (Nektar)
7F                    # Device ID (broadcast)
01                    # Command (SET=0x01, GET=0x02)
01                    # Target (PRESET=0x01, GLOBAL=0x05, BACKUP=0x7F)
XX                    # Index (preset 0x00-0x2F = A1-F8)
XX                    # Object (control ID lub 0x7F)
XX                    # Element (parametr)
[data bytes...]       # Dane (zmienne)
XX                    # Checksum
F7                    # SysEx End
```

### Checksum

```python
def checksum(data: bytes) -> int:
    """Suma bajtów od Manufacturer ID do końca danych (bez F0/F7)."""
    return (128 - (sum(data) % 128)) % 128
```

### Stałe (z pacer-editor/src/pacer/constants.js)

```python
# Komendy
CMD_SET = 0x01
CMD_GET = 0x02

# Target types
TARGET_PRESET = 0x01
TARGET_GLOBAL = 0x05
TARGET_BACKUP = 0x7F

# Control IDs (stompswitches)
SW1, SW2, SW3, SW4, SW5, SW6 = 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12

# Message types
MSG_CTRL_OFF = 0x61       # Kontrolka wyłączona
MSG_SW_NOTE = 0x43        # Note on/off
MSG_SW_PRG_BANK = 0x45    # Program Change + Bank SELECT (preset!)
MSG_AD_MIDI_CC = 0x00     # Control Change (CC)
MSG_SW_MMC = 0x55         # MIDI Machine Control

# LED colors
LED_OFF = 0x00
LED_RED = 0x03
LED_GREEN = 0x0D
LED_BLUE = 0x11
LED_WHITE = 0x17

# Preset indices: A1=0x00, A2=0x01, ..., F8=0x2F (6×8 = 48 presetów)
```

### Typy wiadomości (Object IDs)

```python
OBJ_PRESET_NAME = 0x7F    # Nazwa presetu (max 8 znaków ASCII)
OBJ_CONTROL_STEP = 0x01   # Konfiguracja kroku kontrolki
OBJ_CONTROL_LED = 0x02    # Konfiguracja LED
OBJ_CONTROL_MODE = 0x03   # Tryb kontrolki (sequence/step)
```

### Przykład: Ustaw nazwę presetu A1 na "SONG"

```
F0 00 01 77 7F 01 01 00 7F 00  # Header + preset A1, object=name
53 4F 4E 47 20 20 20 20        # "SONG    " (8 bajtów, padded)
XX                              # Checksum
F7                              # End
```

### Przykład: Ustaw SW1 step 1 → Program Change 5 na kanale 0

```
F0 00 01 77 7F 01 01 00 0D 01  # Header + SW1 (0x0D), step 1
45 00 05 00 00 01               # msg_type=0x45, channel=0, program=5, active=1
XX                              # Checksum
F7
```

## Moduł pacer/

### Struktura plików

```
src/paternologia/pacer/
├── __init__.py       # Eksporty publiczne
├── constants.py      # Stałe protokołu (powyżej)
├── sysex.py          # PacerSysExBuilder
├── mappings.py       # Translacja Paternologia → MIDI
└── export.py         # Song → .syx (główna funkcja)
```

### constants.py

```python
"""Stałe protokołu Nektar Pacer SysEx."""

SYSEX_START = 0xF0
SYSEX_END = 0xF7
MANUFACTURER_ID = bytes([0x00, 0x01, 0x77])
DEVICE_ID = 0x7F

CMD_SET = 0x01
CMD_GET = 0x02

TARGET_PRESET = 0x01
TARGET_GLOBAL = 0x05

# Control IDs
STOMPSWITCHES = {i: 0x0D + i for i in range(6)}  # SW1-SW6

# Message types
MSG_SW_PRG_BANK = 0x45  # Preset/Pattern
MSG_AD_MIDI_CC = 0x00   # CC

# LED
LED_OFF = 0x00
LED_GREEN = 0x0D

# Objects
OBJ_PRESET_NAME = 0x7F
OBJ_CONTROL_STEP = 0x01

# Preset mapping: "A1" -> 0x00, "F8" -> 0x2F
PRESET_INDICES = {
    f"{row}{col}": (ord(row) - ord('A')) * 8 + (col - 1)
    for row in "ABCDEF" for col in range(1, 9)
}
```

### sysex.py

```python
"""Generator wiadomości SysEx dla Nektar Pacer."""

from . import constants as c

def checksum(data: bytes) -> int:
    return (128 - (sum(data) % 128)) % 128

class PacerSysExBuilder:
    """Buduje pojedyncze wiadomości SysEx."""

    def __init__(self, preset_index: int):
        self.preset_index = preset_index

    def _build(self, obj_id: int, element: int, data: bytes) -> bytes:
        """Ramka SysEx z checksum."""
        header = bytes([
            c.DEVICE_ID,
            c.CMD_SET,
            c.TARGET_PRESET,
            self.preset_index,
            obj_id,
            element
        ])
        payload = c.MANUFACTURER_ID + header + data
        cs = checksum(payload)
        return bytes([c.SYSEX_START]) + payload + bytes([cs, c.SYSEX_END])

    def build_preset_name(self, name: str) -> bytes:
        """Ustaw nazwę presetu (max 8 ASCII)."""
        ascii_name = name.encode('ascii', errors='replace')[:8].ljust(8, b' ')
        return self._build(c.OBJ_PRESET_NAME, 0x00, ascii_name)

    def build_control_step(
        self,
        control_id: int,
        step_index: int,
        msg_type: int,
        channel: int,
        data1: int,
        data2: int = 0,
        data3: int = 0,
        active: bool = True
    ) -> bytes:
        """Konfiguruj krok kontrolki."""
        data = bytes([msg_type, channel, data1, data2, data3, int(active)])
        return self._build(control_id, step_index, data)
```

### mappings.py

```python
"""Mapowanie Paternologia → MIDI."""

from ..models import Action, ActionType
from . import constants as c

# Hardcoded w MVP - do przeniesienia do devices.yaml w następnej iteracji
DEVICE_CHANNELS = {
    "boss": 0,
    "ms": 1,
    "freak": 2,
}

def get_device_channel(device_id: str) -> int:
    return DEVICE_CHANNELS.get(device_id, 0)

def action_to_midi(action: Action) -> tuple[int, int, int, int]:
    """
    Konwertuj Action na parametry MIDI.

    Returns:
        (msg_type, channel, data1, data2)
    """
    channel = get_device_channel(action.device)

    if action.type == ActionType.PRESET:
        # Program Change + Bank
        return (c.MSG_SW_PRG_BANK, channel, action.value, 0)

    elif action.type == ActionType.PATTERN:
        # Pattern to też Program Change (inne bank?)
        return (c.MSG_SW_PRG_BANK, channel, action.value, 0)

    elif action.type == ActionType.CC:
        # Control Change
        return (c.MSG_AD_MIDI_CC, channel, action.cc or 0, action.value)

    else:
        raise ValueError(f"Nieobsługiwany typ akcji: {action.type}")
```

### export.py

```python
"""Eksport Song → .syx."""

from ..models import Song
from .sysex import PacerSysExBuilder
from .mappings import action_to_midi
from . import constants as c

def export_song_to_syx(song: Song, target_preset: str = "A1") -> bytes:
    """
    Eksportuj piosenkę do pliku .syx.

    Args:
        song: Piosenka z Paternologii
        target_preset: Preset docelowy (A1-F8)

    Returns:
        bytes: Zawartość pliku .syx (konkatenacja wiadomości)
    """
    preset_index = c.PRESET_INDICES[target_preset.upper()]
    builder = PacerSysExBuilder(preset_index)
    messages = []

    # 1. Nazwa presetu
    messages.append(builder.build_preset_name(song.song.name))

    # 2. Konfiguracja przycisków SW1-SW6
    for btn_idx, button in enumerate(song.pacer[:6]):
        control_id = c.STOMPSWITCHES[btn_idx]

        # Kroki (max 6 akcji)
        for step_idx, action in enumerate(button.actions[:6], start=1):
            msg_type, channel, data1, data2 = action_to_midi(action)
            messages.append(builder.build_control_step(
                control_id=control_id,
                step_index=step_idx,
                msg_type=msg_type,
                channel=channel,
                data1=data1,
                data2=data2,
                active=True
            ))

    return b"".join(messages)
```

## API

### Router: routers/pacer.py

```python
"""Endpoint eksportu .syx."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from ..storage import get_song, get_devices
from .pacer.export import export_song_to_syx

router = APIRouter(prefix="/pacer", tags=["pacer"])

@router.get("/export/{song_id}.syx")
def export_syx(song_id: str, preset: str = "A1"):
    """Eksportuj piosenkę do .syx."""
    song = get_song(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    # Walidacja preset
    if not preset.upper() in ["A1", "A2", ..., "F8"]:  # lub z constants
        raise HTTPException(400, f"Invalid preset: {preset}")

    syx_data = export_song_to_syx(song, preset)

    return Response(
        content=syx_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{song_id}_{preset}.syx"'
        }
    )
```

### Rejestracja w main.py

```python
from .routers import pacer

app.include_router(pacer.router)
```

## UI

### Template: song.html (rozszerzenie)

```html
<section class="pacer-export">
    <h3>Export to Pacer</h3>

    <label for="preset">Target Preset:</label>
    <select id="preset">
        {% for row in "ABCDEF" %}
            {% for col in range(1, 9) %}
                <option value="{{ row }}{{ col }}">{{ row }}{{ col }}</option>
            {% endfor %}
        {% endfor %}
    </select>

    <a id="download-syx"
       href="/pacer/export/{{ song.song.id }}.syx?preset=A1"
       download="{{ song.song.id }}_A1.syx"
       class="button">
        Download .syx file
    </a>

    <details class="instructions">
        <summary>Usage</summary>
        <ol>
            <li>List MIDI ports: <code>amidi -l</code></li>
            <li>Send to Pacer: <code>amidi -p hw:X,0,0 -s <em>filename.syx</em></code></li>
            <li>Replace <strong>hw:X,0,0</strong> with your PACER port</li>
        </ol>
    </details>
</section>

<script>
document.getElementById('preset').addEventListener('change', (e) => {
    const preset = e.target.value;
    const link = document.getElementById('download-syx');
    link.href = `/pacer/export/{{ song.song.id }}.syx?preset=${preset}`;
    link.download = `{{ song.song.id }}_${preset}.syx`;
});
</script>
```

## Testowanie

### Testy jednostkowe

**test_pacer_sysex.py:**
```python
from paternologia.pacer.sysex import PacerSysExBuilder, checksum

def test_checksum():
    data = bytes([0x00, 0x01, 0x77, 0x7F, 0x01])
    cs = checksum(data)
    assert 0 <= cs < 128

def test_preset_name():
    builder = PacerSysExBuilder(0x00)  # A1
    syx = builder.build_preset_name("TEST")

    assert syx[0] == 0xF0
    assert syx[-1] == 0xF7
    assert syx[1:4] == bytes([0x00, 0x01, 0x77])
    assert b"TEST" in syx

def test_control_step():
    builder = PacerSysExBuilder(0x00)
    syx = builder.build_control_step(
        control_id=0x0D,  # SW1
        step_index=1,
        msg_type=0x45,
        channel=0,
        data1=5,
        active=True
    )

    assert len(syx) > 10
    assert syx[6] == 0x01  # TARGET_PRESET
```

**test_pacer_mappings.py:**
```python
from paternologia.pacer.mappings import action_to_midi
from paternologia.models import Action, ActionType

def test_preset_action():
    action = Action(device="boss", type=ActionType.PRESET, value=5)
    msg_type, channel, data1, data2 = action_to_midi(action)

    assert msg_type == 0x45  # MSG_SW_PRG_BANK
    assert channel == 0      # boss channel
    assert data1 == 5

def test_cc_action():
    action = Action(device="ms", type=ActionType.CC, cc=74, value=127)
    msg_type, channel, data1, data2 = action_to_midi(action)

    assert msg_type == 0x00  # MSG_AD_MIDI_CC
    assert channel == 1      # ms channel
    assert data1 == 74
    assert data2 == 127
```

**test_pacer_export.py:**
```python
from paternologia.pacer.export import export_song_to_syx
from paternologia.models import Song, PacerButton, Action, ActionType

def test_export_minimal(tmp_path):
    song = Song(
        song={"id": "test", "name": "TEST"},
        pacer=[
            PacerButton(
                name="Btn1",
                actions=[Action(device="boss", type=ActionType.PRESET, value=1)]
            )
        ]
    )

    syx = export_song_to_syx(song, "A1")

    assert len(syx) > 0
    assert syx[0] == 0xF0
    assert syx[-1] == 0xF7
    assert b"TEST" in syx
```

### Test API

**test_pacer_api.py:**
```python
def test_export_endpoint(client, sample_song):
    response = client.get(f"/pacer/export/{sample_song.song.id}.syx?preset=B3")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content[0] == 0xF0

def test_export_404(client):
    response = client.get("/pacer/export/nonexistent.syx")
    assert response.status_code == 404
```

### Test manualny z pacer-editor

```bash
# 1. Wygeneruj .syx
curl -o test.syx http://localhost:8000/pacer/export/w-ciszy.syx?preset=A1

# 2. Uruchom pacer-editor
cd workspace/pacer-editor
NODE_OPTIONS=--openssl-legacy-provider yarn start

# 3. Przeciągnij test.syx do przeglądarki (http://localhost:3000)
# 4. Weryfikuj wizualnie:
#    - Nazwa presetu = nazwa piosenki
#    - SW1-SW6 mają odpowiednie akcje
#    - Typy akcji (Program Change, CC) są poprawne

# 5. Hexdump porównanie
hexdump -C test.syx
```

## Plan implementacji

### Iteracja 1: Fundament (3-4h)
- [ ] Utworzyć `src/paternologia/pacer/` z plikami
- [ ] `constants.py` - wszystkie stałe z pacer-editor
- [ ] `sysex.py` - `PacerSysExBuilder` + checksum
- [ ] Testy jednostkowe: `test_pacer_sysex.py`

### Iteracja 2: Mapowanie (2h)
- [ ] `mappings.py` - `DEVICE_CHANNELS`, `action_to_midi()`
- [ ] Testy: `test_pacer_mappings.py`

### Iteracja 3: Eksport (2-3h)
- [ ] `export.py` - `export_song_to_syx()`
- [ ] Testy: `test_pacer_export.py`
- [ ] Test manualny: hexdump wygenerowanego pliku

### Iteracja 4: API (1-2h)
- [ ] `routers/pacer.py` - endpoint GET
- [ ] Rejestracja w `main.py`
- [ ] Testy API: `test_pacer_api.py`

### Iteracja 5: UI (1h)
- [ ] Rozszerzenie `templates/song.html`
- [ ] Test E2E: klik → pobierz → hexdump

### Iteracja 6: Walidacja (1-2h)
- [ ] Test z pacer-editor (wizualna weryfikacja)
- [ ] Test z amidi (jeśli Pacer dostępny)

**Łączny czas: ~10-14h**

## Referencje

- `workspace/pacer-editor/` (git submodule)
- `workspace/pacer-editor/src/pacer/constants.js` - stałe protokołu
- `workspace/pacer-editor/src/pacer/sysex.js` - algorytm checksum, budowanie ramek
- `workspace/pacer-editor/sysex.md` - dokumentacja protokołu
- `SPEC_PACER_BRIDGE.md` - kontekst workflow amidi

## Zmiany względem v1

1. ✅ Ujednolicone wartości MIDI (0x45 dla preset, 0x00 dla CC)
2. ✅ Algorytm checksum z pacer-editor
3. ✅ Pełna struktura ramki SysEx (F0...F7)
4. ✅ Hardcoded `DEVICE_CHANNELS` w mappings.py (MVP)
5. ✅ Normalizacja nazw presetów (8 znaków ASCII)
6. ✅ Format pliku: konkatenacja wiadomości bez separatorów
7. ✅ UI: instrukcja `amidi -l` zamiast hardcoded portu
8. ✅ Referencja do pacer-editor przez submodule
