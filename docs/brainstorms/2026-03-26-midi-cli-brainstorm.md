# Brainstorm: CLI do sterowania i programowania urządzeń MIDI

**Data:** 2026-03-26
**Status:** Draft

## Co budujemy

CLI (`uv run paternologia <command>`) jako moduł wewnątrz pakietu Paternologia, umożliwiające:

1. **Programowanie RC-600** — generowanie plików konfiguracyjnych XML (MEMORY.RC0) z definicji YAML i transfer na urządzenie przez USB Storage
2. **Sterowanie runtime MIDI** — wysyłanie Program Change (przełączanie memory) i CC do RC-600 w czasie rzeczywistym

Poza scope pierwszej wersji: Pacer CLI (eksport/wysyłanie SysEx) — Pacer działa już przez web i nie jest pain pointem. Można dodać później.

## Dlaczego to podejście

### Problem
Wojciech konfiguruje RC-600 (efekty, assigny, parametry) ręcznie przez menu urządzenia przed każdą piosenką. Ma ~3-5 bazowych szablonów konfiguracji, które modyfikuje per piosenka. To jest czasochłonne i podatne na błędy.

### Odkrycia z researchu
- **RC-600 nie wspiera SysEx** do programowania — konfiguracja odbywa się przez pliki XML (MEMORY.RC0) na USB Storage
- Istnieje projekt open-source `shaenzi/boss_rc600` (Python) do manipulacji plikami XML RC-600
- RC-600 wspiera MIDI Program Change (przełączanie 99 memory) i CC Assign (sterowanie funkcjami)
- Pacer ma już pełną implementację SysEx w Paternologii

### Wybór architektury: moduł wewnątrz Paternologii
- Współdzielone modele Pydantic, storage YAML, infrastruktura MIDI (python-rtmidi) — zero duplikacji (DRY)
- Jeden pakiet, jeden `pyproject.toml`, jeden zestaw testów (KISS)
- Osobny pakiet byłby overengineeringiem na tym etapie

## Kluczowe decyzje

### 1. Definicja konfiguracji RC-600 per piosenka
**Osobne pliki YAML** w `data/rc600/<song-id>.yaml`, linkowane z piosenką przez song ID (nazwa pliku = song ID, tak jak w `data/songs/`).

Dokładny format YAML zależy od struktury XML w plikach MEMORY.RC0 — trzeba ją zbadać przed implementacją. Wstępny szkic (do weryfikacji):

```yaml
# data/rc600/w-ciszy.yaml — format wstępny, do weryfikacji po analizie MEMORY.RC0
memory: 15
input_fx:
  - type: compressor
    threshold: -20
track_fx:
  - type: reverb
    level: 60
assigns:
  - source: CC#1
    target: track1_volume
```

### 2. Transfer na RC-600
Dwuetapowy workflow:
1. CLI modyfikuje konkretne memory (slot 1-99) w pliku MEMORY.RC0 (XML) na podstawie YAML definicji
2. Kopiuje zmodyfikowany plik na urządzenie przez USB Storage

Ważne: MEMORY.RC0 zawiera wszystkie 99 memory. `generate` musi czytać istniejący plik, modyfikować wybrany slot, i zapisywać z powrotem — nie generować od zera.

### 3. Sterowanie runtime
Przez MIDI (python-rtmidi) — Program Change do przełączania memory, CC do sterowania assignami.

### 4. Scope pierwszej wersji
- Tylko RC-600 (Pacer już działa przez web)
- Offline konfiguracja (XML) + runtime sterowanie (MIDI)
- Inne urządzenia (Model:Samples, MicroFreak) — później
- `pull` (import z urządzenia) — później, wymaga odwrotnego parsera XML→YAML

### 5. Kryterium sukcesu
Pierwsza wersja działa, gdy: mogę zdefiniować konfigurację RC-600 dla piosenki w YAML, wygenerować MEMORY.RC0, skopiować na urządzenie, i RC-600 załaduje poprawne efekty/assigny po restarcie.

## Proponowana struktura komend CLI

Uruchamianie: `uv run paternologia <grupa> <komenda> [argumenty]`

```
# RC-600 — offline konfiguracja (USB Storage)
paternologia rc600 generate <song> # generuj MEMORY.RC0 z YAML definicji
paternologia rc600 push <song>     # skopiuj konfigurację na urządzenie (USB)
# paternologia rc600 pull           # v2 — wymaga parsera XML→YAML

# RC-600 — runtime sterowanie (MIDI)
paternologia rc600 send-pc <memory> # wyślij Program Change (przełącz memory)
paternologia rc600 send-cc <cc> <value> # wyślij CC

# Pacer — poza scope v1 (działa przez web)
# paternologia pacer send <song>
# paternologia pacer export <song>
```

## Open Questions

1. **Format XML RC-600 (blocker)** — trzeba zbadać dokładną strukturę plików MEMORY.RC0 zanim będzie można zaprojektować format YAML. Krok: zrobić backup RC-600 przez USB, przeanalizować XML, porównać z `shaenzi/boss_rc600`. Bez tego nie da się sensownie planować.
2. **Walidacja konfiguracji** — jak walidować wartości parametrów efektów? Prawdopodobnie wyniknie z analizy XML (zakresy wartości powinny być widoczne w strukturze danych).
3. **Framework CLI** — `typer`, `click`, czy wbudowany `argparse`? Decyzja na etapie planowania.

## Resolved Questions

- **USB Storage automount** — do sprawdzenia przy implementacji. Workflow może wymagać ręcznego przełączenia RC-600 w tryb Storage.
- **Szablony** — na początek pełna definicja per piosenka (bez dziedziczenia). Szablony mogą zostać dodane w przyszłości gdy będzie potrzeba.
