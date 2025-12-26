# ABOUTME: Specyfikacja high-level dla eksportu plików .syx z Paternologii (Faza 2)
# ABOUTME: Architektura i struktura modułu pacer/ oraz integracja z istniejącym systemem

# Specyfikacja: Export .syx z Paternologii

## Cel

Dodanie funkcjonalności eksportu ustawień piosenki z Paternologii do formatu `.syx` (MIDI SysEx), który można następnie wgrać do urządzenia Nektar Pacer za pomocą `amidi` lub podejrzeć/edytować w `pacer-editor`.

## Zakres (Faza 2 z SPEC_PACER_BRIDGE.md)

**Co implementujemy:**
- Generator wiadomości SysEx zgodnych z protokołem Nektar Pacer
- Funkcję konwersji modelu `Song` → plik `.syx`
- API endpoint do pobierania pliku `.syx` dla danej piosenki
- Interfejs użytkownika do inicjacji eksportu

**Co NIE jest w zakresie (do późniejszych faz):**
- Bezpośrednie wysyłanie do Pacera przez Web MIDI (nie działa na Ubuntu)
- Integracja z pacer-editor przez iframe/postMessage
- Automatyczna synchronizacja
- Zaawansowana konfiguracja LED/kolorystyki

## Architektura rozwiązania

### 1. Struktura modułu `pacer/`

Nowy moduł w `src/paternologia/pacer/` z następującymi komponentami:

```
src/paternologia/pacer/
├── __init__.py           # Eksportuje publiczne API modułu
├── constants.py          # Stałe protokołu Pacer (Pacer-specific)
├── sysex.py              # Klasa PacerSysExBuilder (niskopoziomowy generator)
├── export.py             # Logika konwersji Song → .syx (wysokopoziomowa)
└── mappings.py           # Mapowanie device/action → MIDI parametry
```

### 2. Odpowiedzialności poszczególnych modułów

#### `constants.py` - Stałe protokołu Pacer
**Cel:** Definicje wszystkich stałych używanych w protokole SysEx Nektar Pacer.

**Zawartość:**
- Manufacturer ID: `0x00 0x01 0x77`
- Komendy: `CMD_SET = 0x01`, `CMD_GET = 0x02`
- Typy celów: `TARGET_PRESET = 0x01`, `TARGET_GLOBAL = 0x02`
- Control IDs: `SW1 = 0x0D`, `SW2 = 0x0E`, ..., `SW6 = 0x12`
- Typy wiadomości MIDI: `MSG_PROGRAM_CHANGE = 0x43`, `MSG_CC = 0x47`
- Preset index mapping: `A1 = 0x00`, `A2 = 0x01`, ..., `F8 = 0x2F`
- LED kolory: `LED_OFF = 0x00`, `LED_GREEN = 0x0D`, `LED_RED = 0x0C`

**Filozofia:** Wszystkie "magic numbers" z protokołu Pacer w jednym miejscu.

#### `sysex.py` - Generator wiadomości SysEx
**Cel:** Niskopoziomowa klasa do budowania pojedynczych wiadomości SysEx.

**Kluczowa klasa:**
```python
class PacerSysExBuilder:
    """Buduje pojedyncze wiadomości SysEx dla Nektar Pacer."""

    def __init__(self, preset_index: int):
        """
        Args:
            preset_index: Indeks presetu (0x00-0x2F dla A1-F8)
        """

    def build_preset_name(self, name: str) -> bytes:
        """Generuje SysEx do ustawienia nazwy presetu."""

    def build_control_step(
        self,
        control_id: int,
        step_index: int,
        channel: int,
        msg_type: int,
        data1: int,
        data2: int,
        data3: int,
        active: bool
    ) -> bytes:
        """Generuje SysEx do konfiguracji pojedynczego kroku kontrolki."""

    def build_control_led(
        self,
        control_id: int,
        step_index: int,
        midi_ctrl: int,
        active_color: int,
        inactive_color: int
    ) -> bytes:
        """Generuje SysEx do konfiguracji LED kontrolki."""

    def build_control_mode(self, control_id: int, mode: int) -> bytes:
        """Generuje SysEx do ustawienia trybu kontrolki."""
```

**Filozofia:** Jedna klasa odpowiedzialna TYLKO za generowanie poprawnych bajtów SysEx. Nie zna nic o modelach Paternologii.

#### `mappings.py` - Mapowanie Paternologia → MIDI
**Cel:** Tłumaczenie konceptów z Paternologii na parametry MIDI/Pacer.

**Kluczowe funkcje:**
```python
def preset_name_to_index(preset: str) -> int:
    """A1 -> 0x00, B3 -> 0x0A, etc."""

def get_device_channel(device_id: str) -> int:
    """Zwraca kanał MIDI dla danego urządzenia (boss -> 0, ms -> 1, etc.)."""

def action_type_to_midi(action: Action) -> int:
    """Konwertuje ActionType na MIDI message type (preset -> 0x45, cc -> 0x47)."""

def get_data_bytes(action: Action) -> tuple[int, int, int]:
    """Ekstrahuje data1, data2, data3 z Action (zależnie od typu)."""
```

**Filozofia:** Warstwa translacji między domeną "piosenki w Paternologii" a domeną "protokół MIDI/Pacer". Wszystkie decyzje mapowania w jednym miejscu.

**Mapowanie urządzeń na kanały MIDI:**
- To wymaga rozszerzenia modelu `Device` o pole `midi_channel: int | None`
- Lub tymczasowo: hardcoded mapping w mappings.py z możliwością przeniesienia do konfiguracji później

#### `export.py` - Konwersja Song → .syx
**Cel:** Wysokopoziomowa logika konwersji obiektu `Song` na kompletny plik `.syx`.

**Kluczowa funkcja:**
```python
def export_song_to_syx(
    song: Song,
    target_preset: str = "A1",
    devices: list[Device] | None = None
) -> bytes:
    """
    Eksportuje piosenkę do pliku .syx.

    Args:
        song: Obiekt piosenki z Paternologii
        target_preset: Docelowy preset w Pacerze (A1-F8)
        devices: Lista urządzeń (do mapowania device_id -> MIDI channel)

    Returns:
        bytes: Pełna zawartość pliku .syx (konkatenacja wielu wiadomości SysEx)
    """
```

**Proces konwersji:**
1. Konwersja target_preset → preset_index
2. Utworzenie PacerSysExBuilder(preset_index)
3. Generacja wiadomości SysEx dla nazwy presetu (z song.song.name)
4. Iteracja po song.pacer (max 6 przycisków)
   - Mapowanie button index → control_id (SW1-SW6)
   - Iteracja po button.actions (max 6 akcji)
     - Mapowanie action → MIDI parametry (channel, msg_type, data bytes)
     - Generacja SysEx dla control_step
   - Generacja SysEx dla LED (domyślnie: aktywny=zielony, nieaktywny=off)
   - Generacja SysEx dla control_mode (wszystkie kroki aktywne)
5. Konkatenacja wszystkich wiadomości SysEx w jeden bufor bajtów
6. Zwrócenie bytes

**Filozofia:** Orkiestracja całego procesu. Używa `sysex.py` do generowania, `mappings.py` do translacji, ale samo operuje na modelach Paternologii.

### 3. Nowy router: `routers/pacer.py`

**Cel:** API endpoint do eksportu piosenki jako plik `.syx`.

**Endpoint:**
```python
@router.get("/pacer/export/{song_id}.syx")
def export_syx(song_id: str, preset: str = "A1"):
    """
    Eksportuj piosenkę do pliku .syx.

    Args:
        song_id: ID piosenki (z storage)
        preset: Docelowy preset w Pacerze (query param, domyślnie A1)

    Returns:
        Response z content-type: application/octet-stream
        i header Content-Disposition: attachment; filename="..."
    """
```

**Proces:**
1. Pobranie song z storage (404 jeśli nie istnieje)
2. Pobranie devices z storage (do mapowania)
3. Wywołanie `export_song_to_syx(song, preset, devices)`
4. Zwrócenie Response z odpowiednimi headerami

**Filozofia:** Cienka warstwa HTTP. Cała logika biznesowa w `export.py`.

### 4. Integracja z UI

**Lokalizacja:** Rozszerzenie template `templates/song.html` (widok piosenki).

**Nowe elementy:**
```html
<div class="pacer-export-section">
    <h3>Export to Pacer</h3>

    <label for="preset-select">Target Preset:</label>
    <select id="preset-select">
        <option value="A1">A1</option>
        <option value="A2">A2</option>
        <!-- ... A1-F8 (48 opcji) -->
    </select>

    <a id="download-syx-link"
       href="/pacer/export/{{ song.song.id }}.syx?preset=A1"
       download="{{ song.song.id }}_A1.syx"
       class="button">
        Download .syx file
    </a>

    <div class="instructions">
        <p>After downloading:</p>
        <code>amidi -p hw:8,0,0 -s {{ song.song.id }}_A1.syx</code>
    </div>
</div>

<script>
// Update link when preset changes
document.getElementById('preset-select').addEventListener('change', (e) => {
    const preset = e.target.value;
    const link = document.getElementById('download-syx-link');
    link.href = `/pacer/export/{{ song.song.id }}.syx?preset=${preset}`;
    link.download = `{{ song.song.id }}_${preset}.syx`;
});
</script>
```

**Filozofia:** Minimalistyczny UI. Użytkownik wybiera preset, pobiera plik, używa `amidi` w terminalu.

## Rozszerzenia modeli (opcjonalne dla MVP)

### Dodanie `midi_channel` do `Device`

**Czy niezbędne w MVP:** NIE. Można użyć hardcoded mapping w `mappings.py`.

**Jeśli implementować:**
```python
class Device(BaseModel):
    id: str
    name: str
    description: str = ""
    action_types: list[ActionType] = []
    midi_channel: int | None = Field(default=None, description="MIDI channel (0-15)")
```

**Modyfikacja `data/devices.yaml`:**
```yaml
devices:
  - id: boss
    name: Boss RC-600
    midi_channel: 0
  - id: ms
    name: Model:Samples
    midi_channel: 1
  - id: freak
    name: MicroFreak
    midi_channel: 2
```

**Zalety:** Elastyczność, konfigurowalność.
**Wady:** Więcej kodu, wymaga migracji danych.
**Decyzja:** Zacząć od hardcoded, dodać później jeśli potrzebne.

## Plan testowania

### Testy jednostkowe

**`tests/test_pacer_sysex.py`** - Test `PacerSysExBuilder`:
- `test_build_preset_name()` - sprawdza strukturę SysEx i kodowanie nazwy
- `test_build_control_step()` - sprawdza parametry control step
- `test_build_control_led()` - sprawdza konfigurację LED
- `test_build_control_mode()` - sprawdza ustawienie trybu

**`tests/test_pacer_mappings.py`** - Test `mappings.py`:
- `test_preset_name_to_index()` - A1→0x00, F8→0x2F
- `test_get_device_channel()` - boss→0, ms→1, freak→2
- `test_action_type_to_midi()` - preset→0x45, cc→0x47
- `test_get_data_bytes()` - różne typy akcji

**`tests/test_pacer_export.py`** - Test `export.py`:
- `test_export_song_to_syx()` - kompletna konwersja Song → bytes
- `test_export_respects_preset_target()` - różne presety docelowe
- `test_export_handles_empty_buttons()` - puste przyciski/akcje

### Testy integracyjne

**`tests/test_pacer_api.py`** - Test API endpoint:
- `test_export_endpoint_returns_syx()` - HTTP 200, content-type, headers
- `test_export_endpoint_404_for_missing_song()` - nieistniejąca piosenka
- `test_export_endpoint_with_preset_param()` - query param preset

### Testy manualne

**Test z `pacer-editor`:**
1. Uruchomić `pacer-editor` lokalnie
2. Wyeksportować piosenkę z Paternologii (np. `w-ciszy_A1.syx`)
3. Przeciągnąć plik do `pacer-editor`
4. Sprawdzić wizualnie:
   - Nazwa presetu odpowiada nazwie piosenki
   - Przyciski SW1-SW6 mają odpowiednie akcje
   - Typy akcji są poprawne (Program Change, CC)
5. Zapisać z `pacer-editor` i porównać z oryginałem (diff hex)

**Test z `amidi` (wymaga Pacer):**
1. Backup obecnej konfiguracji Pacera
2. Wyeksportować piosenkę do A1
3. Wysłać: `amidi -p hw:8,0,0 -s w-ciszy_A1.syx`
4. Sprawdzić na Pacerze:
   - Preset A1 ma nazwę piosenki
   - Przyciski działają zgodnie z konfiguracją
   - MIDI akcje są wysyłane poprawnie

## Kolejność implementacji (priorytet)

### Iteracja 1: Fundament (MVP - ~3-4h)
1. **Utworzyć strukturę katalogów i pliki** (`pacer/constants.py`, `pacer/sysex.py`)
2. **Zaimplementować `PacerSysExBuilder`** (podstawowe typy: preset name, control step)
3. **Napisać testy jednostkowe** dla `PacerSysExBuilder`
4. **Zaimplementować `mappings.py`** (hardcoded device channels)
5. **Napisać testy** dla `mappings.py`

### Iteracja 2: Konwersja (MVP - ~2-3h)
1. **Zaimplementować `export_song_to_syx()`** w `export.py`
2. **Napisać testy jednostkowe** dla `export.py`
3. **Test manualny** z przykładową piosenką (w-ciszy.yaml → .syx → hex dump)

### Iteracja 3: API i UI (MVP - ~1-2h)
1. **Utworzyć router** `routers/pacer.py` z endpointem `/pacer/export`
2. **Dodać routing** w `main.py` (`app.include_router(pacer.router)`)
3. **Napisać testy API** (`test_pacer_api.py`)
4. **Rozszerzyć template** `song.html` o sekcję eksportu
5. **Test E2E** - kliknięcie w UI → pobierz plik → sprawdź zawartość

### Iteracja 4: Walidacja (MVP - ~1h)
1. **Test z pacer-editor** - załadować wygenerowany .syx, sprawdzić wizualnie
2. **Test z amidi** (opcjonalnie, jeśli Pacer dostępny) - wgrać do sprzętu

### Iteracja 5: Dopracowanie (post-MVP)
1. **Dodać `midi_channel` do modelu Device** (jeśli potrzebne)
2. **Migrować hardcoded channels** z `mappings.py` do `devices.yaml`
3. **Dodać więcej typów wiadomości MIDI** (Bank Select, SysEx passthrough)
4. **Rozbudować konfigurację LED** (kolory, tryby)

## Zależności i wymagania

### Zależności Python
- **Brak nowych zależności** - używamy tylko standardowej biblioteki (`struct` do pakowania bajtów)

### Wymagania systemowe
- **amidi** - do manualnego testowania i użytkowania (już zainstalowane)
- **pacer-editor** - opcjonalnie, do wizualnej weryfikacji (już dostępne w workspace)

### Wymagania od użytkownika
- **Znajomość terminala** - musi użyć `amidi` do wysyłania plików
- **Fizyczne podłączenie Pacer** - do faktycznego wgrania konfiguracji

## Ryzyka i ograniczenia

### Ryzyka techniczne
1. **Protokół SysEx nie jest w pełni udokumentowany** - może wymagać reverse engineering z pacer-editor
2. **Checksumowanie wiadomości** - protokół Pacer może wymagać checksum (do weryfikacji)
3. **Timing wiadomości** - niektóre urządzenia MIDI wymagają opóźnień między wiadomościami

### Ograniczenia MVP
1. **Brak automatycznego wysyłania** - użytkownik musi użyć terminala
2. **Brak walidacji przed wysłaniem** - użytkownik może wgrać niepoprawną konfigurację
3. **Brak backup/restore w UI** - użytkownik musi sam zarządzać backupami przez amidi
4. **Brak wizualnego podglądu** - użytkownik nie widzi efektu przed wgraniem do sprzętu

### Mitigacja ryzyk
- **Testy z pacer-editor** - używamy istniejącego narzędzia do weryfikacji przed wgraniem do sprzętu
- **Dokumentacja dla użytkownika** - instrukcje w UI jak bezpiecznie użyć `amidi`
- **Backup reminder** - UI przypomina o zrobieniu backupu przed wgraniem

## Metryki sukcesu

### Kryteria akceptacji (Must Have)
- ✅ Wygenerowany plik .syx otwiera się w pacer-editor bez błędów
- ✅ Nazwa presetu w pacer-editor odpowiada nazwie piosenki
- ✅ Liczba przycisków i akcji zgadza się z definicją w Paternologii
- ✅ Typy akcji (preset/pattern/cc) są poprawnie rozpoznawane
- ✅ Endpoint `/pacer/export/{song_id}.syx` zwraca plik do pobrania
- ✅ UI pozwala wybrać preset docelowy (A1-F8)

### Kryteria jakości (Should Have)
- ✅ Test coverage ≥80% dla modułu `pacer/`
- ✅ Wszystkie testy jednostkowe i integracyjne przechodzą
- ✅ Kod zgodny z typowaniem Pydantic (mypy clean)
- ✅ Dokumentacja docstring dla publicznych funkcji

### Kryteria użyteczności (Nice to Have)
- ✅ Plik .syx wgrany do Pacera działa poprawnie (test z fizycznym sprzętem)
- ✅ Użytkownik potrafi wykonać cały workflow bez pomocy (UX test)
- ✅ Czas generowania pliku .syx <100ms dla typowej piosenki

## Podsumowanie

### Co dodajemy
- **Moduł `pacer/`** (4 pliki, ~400 linii kodu)
- **Router `routers/pacer.py`** (~50 linii)
- **UI extension** w `templates/song.html` (~30 linii HTML+JS)
- **Testy** (~300 linii testów)

### Co osiągamy
- Użytkownik może wyeksportować piosenkę z Paternologii do pliku .syx
- Plik .syx można wgrać do Nektar Pacer za pomocą `amidi`
- Plik .syx można podejrzeć/edytować w `pacer-editor`
- System jest testowalny i rozszerzalny

### Następne kroki (post-MVP)
- Dodanie konfiguracji MIDI channels w modelu Device
- Rozbudowa UI o wizualny podgląd (opcjonalnie)
- Integracja z pacer-editor przez iframe/postMessage
- Automatyczny backup przed każdym wgraniem
