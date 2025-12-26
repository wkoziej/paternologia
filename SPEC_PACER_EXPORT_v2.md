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
XX                    # Object (zależy od typu wiadomości - patrz niżej)
[data bytes...]       # Dane (zmienne, zawierają element IDs dla parametrów)
XX                    # Checksum
F7                    # SysEx End
```

**Object byte:**
- Dla **preset name**: `0x01` (CONTROL_NAME)
- Dla **control steps**: `0x0D-0x12` (control ID: SW1-SW6)
- Dla **control mode**: `0x0D-0x12` (control ID)
- Dla **control LED**: `0x0D-0x12` (control ID)

**Uwaga**: NIE MA osobnego bajtu "Element" w headerze! Element IDs są częścią data bytes dla każdego parametru.

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

# Message types (używane w control step data)
MSG_CTRL_OFF = 0x61       # Kontrolka wyłączona
MSG_SW_NOTE = 0x43        # Note on/off
MSG_SW_PRG_BANK = 0x45    # Program Change + Bank Select (PRESET)
MSG_SW_PRG_STEP = 0x46    # Program Step (PATTERN - start/end range)
MSG_AD_MIDI_CC = 0x00     # Control Change (CC)
MSG_SW_MMC = 0x55         # MIDI Machine Control

# LED colors
LED_OFF = 0x00
LED_RED = 0x03
LED_GREEN = 0x0D
LED_BLUE = 0x11
LED_WHITE = 0x17

# Special object IDs
CONTROL_NAME = 0x01       # Object ID dla nazwy presetu
CONTROL_MODE_ELEMENT = 0x60  # Element ID dla trybu kontrolki

# Preset indices: A1=0x00, A2=0x01, ..., F8=0x2F (6×8 = 48 presetów)
```

### Przykład: Ustaw nazwę presetu A1 na "SONG"

```
F0 00 01 77 7F                  # SysEx start + Manufacturer ID
01 01 00 01 00                  # CMD_SET, TARGET_PRESET, index=A1, CONTROL_NAME, element=0
04                              # Długość nazwy (4 bajty)
53 4F 4E 47                     # "SONG" (ASCII: 'S', 'O', 'N', 'G')
XX                              # Checksum
F7                              # SysEx end
```

**Uwaga**: Format `[długość, bajty...]` bez paddingu do 8 znaków (pacer-editor/sysex.js:858)

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

# Control IDs (Object byte dla control steps/mode/LED)
STOMPSWITCHES = {i: 0x0D + i for i in range(6)}  # SW1-SW6

# Special Object IDs
CONTROL_NAME = 0x01  # Object ID dla nazwy presetu

# Element IDs
CONTROL_MODE_ELEMENT = 0x60  # Element dla trybu kontrolki

# Message types (używane w control step data)
MSG_CTRL_OFF = 0x61       # Kontrolka wyłączona
MSG_SW_PRG_BANK = 0x45    # Program Change + Bank (PRESET)
MSG_SW_PRG_STEP = 0x46    # Program Step (PATTERN - start/end)
MSG_AD_MIDI_CC = 0x00     # Control Change (CC)

# LED colors
LED_OFF = 0x00
LED_GREEN = 0x0D
LED_RED = 0x03

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
        """Ustaw nazwę presetu (dynamiczna długość, max 8 ASCII)."""
        ascii_name = name.encode('ascii', errors='replace')[:8]
        # Format: [długość] [bajty ASCII...]
        data = bytes([len(ascii_name)]) + ascii_name
        return self._build(c.CONTROL_NAME, 0x00, data)

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
        """Konfiguruj krok kontrolki.

        Struktura: dla każdego parametru: [element_id, 0x01, wartość, 0x00]
        gdzie element_id = (step_index-1)*6 + offset
        """
        base = (step_index - 1) * 6
        params = []

        # Każdy parametr: [element, object_type=0x01, value, padding=0x00]
        params.extend([base + 1, 0x01, channel, 0x00])      # Channel
        params.extend([base + 2, 0x01, msg_type, 0x00])     # Message type
        params.extend([base + 3, 0x01, data1, 0x00])        # Data 1
        params.extend([base + 4, 0x01, data2, 0x00])        # Data 2
        params.extend([base + 5, 0x01, data3, 0x00])        # Data 3
        params.extend([base + 6, 0x01, int(active)])        # Active (bez paddingu)

        header = bytes([
            c.DEVICE_ID,
            c.CMD_SET,
            c.TARGET_PRESET,
            self.preset_index,
            control_id
        ])
        payload = c.MANUFACTURER_ID + header + bytes(params)
        cs = checksum(payload)
        return bytes([c.SYSEX_START]) + payload + bytes([cs, c.SYSEX_END])
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

def pattern_to_program(value: int | str | None) -> int:
    """Konwertuj pattern ID na Program Change number.

    M:S: A01-A16 (0-15), B01-B16 (16-31), ..., F01-F16 (80-95)
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Format "A01", "B02", etc.
        if len(value) >= 3 and value[0].isalpha():
            bank = ord(value[0].upper()) - ord('A')  # A=0, B=1, ..., F=5
            pattern = int(value[1:]) - 1  # 01→0, 02→1, ..., 16→15
            return bank * 16 + pattern
    return 0  # fallback

def action_to_midi(action: Action) -> tuple[int, int, int, int]:
    """
    Konwertuj Action na parametry MIDI.

    Returns:
        (msg_type, channel, data1, data2)
    """
    channel = get_device_channel(action.device)

    if action.type == ActionType.PRESET:
        # Program Change + Bank
        # data1 = program number, data2 = bank LSB, data3 = bank MSB
        return (c.MSG_SW_PRG_BANK, channel, action.value, 0)

    elif action.type == ActionType.PATTERN:
        # Pattern na Model:Samples = Program Change (jak preset)
        # M:S używa PC 0-95 do wyboru pattern 1-96
        # Konwertuj "A01" → 0, "A02" → 1, etc. (lub int jeśli już number)
        program = pattern_to_program(action.value)
        return (c.MSG_SW_PRG_BANK, channel, program, 0)

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
    for btn_idx in range(6):  # Zawsze przetwarzaj wszystkie 6 przycisków
        control_id = c.STOMPSWITCHES[btn_idx]
        button = song.pacer[btn_idx] if btn_idx < len(song.pacer) else None

        # Zawsze konfiguruj wszystkie 6 kroków (czyszczenie niewykorzystanych)
        for step_idx in range(1, 7):
            if button and step_idx <= len(button.actions):
                # Akcja istnieje - konfiguruj normalnie
                action = button.actions[step_idx - 1]
                msg_type, channel, data1, data2 = action_to_midi(action)
                messages.append(builder.build_control_step(
                    control_id=control_id,
                    step_index=step_idx,
                    msg_type=msg_type,
                    channel=channel,
                    data1=data1,
                    data2=data2,
                    data3=0,
                    active=True
                ))
            else:
                # Brak akcji - wyczyść krok (MSG_CTRL_OFF, active=False)
                messages.append(builder.build_control_step(
                    control_id=control_id,
                    step_index=step_idx,
                    msg_type=c.MSG_CTRL_OFF,
                    channel=0,
                    data1=0,
                    data2=0,
                    data3=0,
                    active=False
                ))

    return b"".join(messages)
```

## API

### Router: routers/pacer.py

```python
"""Endpoint eksportu .syx."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from ..dependencies import get_storage
from ..storage import Storage
from .pacer.export import export_song_to_syx
from .pacer import constants as c

router = APIRouter(prefix="/pacer", tags=["pacer"])

@router.get("/export/{song_id}.syx")
def export_syx(
    song_id: str,
    preset: str = "A1",
    storage: Storage = Depends(get_storage)
):
    """Eksportuj piosenkę do .syx."""
    song = storage.get_song(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    # Walidacja preset
    if preset.upper() not in c.PRESET_INDICES:
        raise HTTPException(400, f"Invalid preset: {preset}. Must be A1-F8.")

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
    """Test happy-path: eksport istniejącej piosenki."""
    response = client.get(f"/pacer/export/{sample_song.song.id}.syx?preset=B3")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content[0] == 0xF0
    assert response.content[-1] == 0xF7

def test_export_404(client):
    """Test: nieistniejąca piosenka zwraca 404."""
    response = client.get("/pacer/export/nonexistent.syx")
    assert response.status_code == 404

def test_export_invalid_preset(client, sample_song):
    """Test: niepoprawny preset zwraca 400."""
    response = client.get(f"/pacer/export/{sample_song.song.id}.syx?preset=Z9")
    assert response.status_code == 400
    assert "Invalid preset" in response.json()["detail"]

def test_export_empty_song(client, storage):
    """Test: piosenka bez akcji generuje puste kroki (MSG_CTRL_OFF)."""
    from paternologia.models import Song
    empty_song = Song(song={"id": "empty", "name": "Empty"}, pacer=[])
    storage.save_song(empty_song)

    response = client.get("/pacer/export/empty.syx")

    assert response.status_code == 200
    # Sprawdź że wszystkie kroki mają MSG_CTRL_OFF (0x61)
    assert b'\x61' in response.content

def test_export_unknown_device(client, storage):
    """Test: nieznane urządzenie używa domyślnego kanału 0."""
    from paternologia.models import Song, PacerButton, Action, ActionType
    song = Song(
        song={"id": "unknown", "name": "Unknown"},
        pacer=[PacerButton(
            name="Btn1",
            actions=[Action(device="unknown_device", type=ActionType.PRESET, value=1)]
        )]
    )
    storage.save_song(song)

    response = client.get("/pacer/export/unknown.syx")

    assert response.status_code == 200
    # Nie powinno rzucić wyjątku, channel=0 jako fallback

def test_export_partial_actions(client, storage):
    """Test: button z 3 akcjami generuje 6 kroków (3 aktywne, 3 wyłączone)."""
    from paternologia.models import Song, PacerButton, Action, ActionType
    song = Song(
        song={"id": "partial", "name": "Partial"},
        pacer=[PacerButton(
            name="Btn1",
            actions=[
                Action(device="boss", type=ActionType.PRESET, value=1),
                Action(device="boss", type=ActionType.PRESET, value=2),
                Action(device="boss", type=ActionType.PRESET, value=3),
            ]
        )]
    )
    storage.save_song(song)

    response = client.get("/pacer/export/partial.syx")

    assert response.status_code == 200
    # Weryfikuj że jest 6 wiadomości control_step dla SW1
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
