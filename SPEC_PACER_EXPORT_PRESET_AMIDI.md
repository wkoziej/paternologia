# ABOUTME: Specyfikacja zapisu domyślnego presetu eksportu i przycisku amidi w widoku piosenki.
# ABOUTME: Dotyczy modeli Song, UI w templates/song.html i nowego endpointu do wysyłki .syx przez amidi.

# Specyfikacja: domyślny preset eksportu + przycisk "Wyślij do Pacer" (amidi)

## Cel

Usprawnić workflow eksportu piosenek do Nektar Pacer poprzez:

1. Zapisywanie domyślnego presetu docelowego per piosenka (żeby nie wybierać go każdorazowo).
2. Dodanie przycisku, który uruchamia `amidi` na odpowiednim porcie i wysyła wygenerowany „w locie” plik `.syx`.

## Zakres

- Zmiana modelu danych piosenki (przechowywanie presetu eksportu).
- UI w widoku piosenki i edycji (preset domyślny + przycisk send).
- Nowy endpoint API do uruchamiania `amidi` na tymczasowym pliku `.syx` wygenerowanym z tych samych danych co eksport.
- Walidacje, obsługa błędów i testy.

## Założenia

- Generowanie `.syx` pozostaje w `src/paternologia/pacer/export.py`.
- `amidi` jest zainstalowane w systemie (pakiet alsa-utils).
- Port docelowy dla Pacera jest konfigurowalny (bez hardcodów w kodzie).

## Zmiany w modelach

### 1) Nowy obiekt ustawień eksportu

W `src/paternologia/models.py` dodać model pomocniczy:

```python
class PacerExportSettings(BaseModel):
    """Ustawienia eksportu/transferu do Pacera."""

    target_preset: str = Field(
        default="A1",
        description="Docelowy preset Pacera (A1-D6)"
    )
```

### 2) Rozszerzenie SongMetadata

```python
class SongMetadata(BaseModel):
    ...
    pacer_export: PacerExportSettings = Field(
        default_factory=PacerExportSettings,
        description="Ustawienia eksportu Pacera"
    )
```

**Uwagi:**
- `target_preset` jest przechowywany per piosenka.
- Port amidi jest konfiguracją systemową (globalną), nie per piosenka.

## Konfiguracja portu amidi

Dodaj plik konfiguracyjny `data/pacer.yaml`:

```yaml
amidi_port: hw:8,0,0
amidi_timeout_seconds: 5
```

Nowy model w `models.py`:

```python
class PacerConfig(BaseModel):
    amidi_port: str = Field(..., description="Domyślny port amidi")
    amidi_timeout_seconds: int = Field(default=5, ge=1, le=30)
```

Nowe metody w `Storage`:
- `get_pacer_config() -> PacerConfig | None`
- `save_pacer_config(config: PacerConfig) -> None`

**Wybór portu:**
1. `data/pacer.yaml` (globalny)
2. brak → endpoint zwraca błąd 400 z komunikatem o konfiguracji portu

## UI: widok piosenki

### 1) Domyślny preset w selectorze

- `select#preset` powinien startować z wartością `song.song.pacer_export.target_preset`.
- Link pobierania `.syx` od razu używa tej wartości.

### 2) Przycisk „Wyślij do Pacer”

- Dodać przycisk obok „Download .syx”.
- Kliknięcie wywołuje nowy endpoint `POST /pacer/send/{song_id}`.
- UI powinien pokazać rezultat (sukces/komunikat błędu) w małym komunikacie pod przyciskami.

Przykład UX:
- `Download .syx` pozostaje bez zmian.
- `Wyślij do Pacer` używa aktualnie wybranego presetu (select).

### 3) BUGFIX: Naprawa zakresu presetów w UI

Obecny kod `song.html` generuje presety A1-F8:
```jinja
{% for row in "ABCDEF" %}
    {% for col in range(1, 9) %}
```

Zmień na A1-D6 (zgodnie z protokołem Pacera):
```jinja
{% for row in "ABCD" %}
    {% for col in range(1, 7) %}
```

## UI: edycja piosenki

W `templates/song_edit.html` (oraz partialach) dodać sekcję ustawień eksportu:

- Pole select `Target Preset` (A1–D6)

Przy zapisie piosenki wartości trafiają do `song.song.pacer_export.*`.

## API: wysyłka przez amidi

### Endpoint

`POST /pacer/send/{song_id}`

**Parametry (query lub JSON):**
- `preset` (opcjonalny) – jeśli podany, nadpisuje zapisany `target_preset`.

**Odpowiedzi:**
- `200 OK` – JSON `{ "status": "ok", "preset": "B3", "port": "hw:8,0,0" }`
- `400 Bad Request` – brak portu/niepoprawny preset
- `404 Not Found` – piosenka nie istnieje
- `500` – błąd uruchomienia `amidi`

### Logika (pseudokod)

```python
@router.post("/pacer/send/{song_id}")
def send_to_pacer(song_id: str, preset: str | None = None):
    song = storage.get_song(song_id) or 404

    target = preset or song.song.pacer_export.target_preset
    validate_preset(target)

    pacer_config = storage.get_pacer_config()
    if not pacer_config:
        raise HTTPException(400, "Missing amidi port configuration in data/pacer.yaml")

    port = pacer_config.amidi_port
    timeout_seconds = pacer_config.amidi_timeout_seconds

    syx = export_song_to_syx(song, storage.get_devices(), target)

    try:
        with NamedTemporaryFile(suffix=".syx", delete=True) as tmp:
            tmp.write(syx)
            tmp.flush()
            run = subprocess.run(
                ["amidi", "-p", port, "-s", tmp.name],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
    except FileNotFoundError:
        raise HTTPException(500, "amidi not found - install alsa-utils package")

    if run.returncode != 0:
        raise HTTPException(500, f"amidi failed: {run.stderr.strip()}")

    return {"status": "ok", "preset": target, "port": port}
```

**Bezpieczeństwo:**
- Port amidi walidowany regexem `^hw:\d+,\d+,\d+$` w modelu `PacerConfig`.
- Uruchamianie tylko przez listę argumentów (bez `shell=True`).
- Timeout (domyślnie 5s) zabezpiecza przed zawieszeniem.

## Walidacje

- `target_preset` musi być w `c.PRESET_INDICES` (walidator w `PacerExportSettings`).
- `amidi_port` w `PacerConfig` musi pasować do wzorca: `^hw:\d+,\d+,\d+$`.

## Zmiany w danych

- Istniejące pliki `data/songs/*.yaml` będą automatycznie kompatybilne dzięki defaultom.
- Przy zapisie piosenki do YAML pojawi się nowy blok:

```yaml
song:
  id: zen
  name: ZEN
  pacer_export:
    target_preset: B3
```

## Testy

### Testy jednostkowe

1. `tests/test_models.py`
   - walidacja `PacerExportSettings` i `PacerConfig`.

2. `tests/test_storage.py`
   - zapis/odczyt `pacer.yaml`.

### Testy API

1. `tests/test_api.py`
   - `POST /pacer/send/{song_id}` zwraca 200 przy poprawnym porcie i presecie.
   - 400 przy błędnym presecie.
   - 400 przy braku konfiguracji `data/pacer.yaml`.
   - 500 gdy `amidi` nie jest zainstalowane (FileNotFoundError).

**Uwaga:** testy endpointu `amidi` powinny mockować `subprocess.run`.

## UI – szczegóły implementacyjne

- `templates/song.html`:
  - `select#preset` ustawiane z `song.song.pacer_export.target_preset`.
  - przycisk `Wyślij do Pacer` wywołuje fetch POST i pokazuje wynik.

- `templates/song_edit.html`:
  - nowe pole select `Target Preset` w sekcji metadanych piosenki.
  - zapis w routerze `songs.py` (parsowanie `pacer_export.target_preset`).

## Decyzje

- Przechowujemy preset w metadanych piosenki, nie w UI state.
- `amidi` uruchamiane tylko po stronie serwera (nie w przeglądarce).
- Plik `.syx` generowany z tych samych danych co eksport i zapisywany do tymczasowego pliku (bez trwałego zapisu w repo).

## Otwarta kwestia (opcjonalna)

Czy w UI dodać listę portów z `amidi -l`? Wymaga endpointu do listowania portów i jest opcjonalne (może być dodane w kolejnym kroku).
