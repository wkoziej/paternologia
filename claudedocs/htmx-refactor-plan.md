# ABOUTME: Plan refaktoryzacji formularzy na HTMX.
# ABOUTME: Zawiera checkboxy do śledzenia postępu implementacji.

# Plan: Refaktoryzacja formularzy na HTMX

**Branch:** `refactor/htmx-forms`
**Data:** 2024-12-27
**Cel:** Zamienić ręczny JavaScript na HTMX, zachowując pełną funkcjonalność

---

## Analiza stanu obecnego

### Co już działa z HTMX
- ✅ HTMX załadowany w `base.html` (v1.9.10)
- ✅ `hx-delete` + `hx-confirm` w `song.html` (usuwanie)
- ✅ `hx-put` w `song_edit.html` (aktualizacja)
- ✅ Endpointy partiali: `/partials/pacer-button`, `/partials/action-row`
- ✅ Szablony partiali: `pacer_button.html`, `action_row.html`

### Co wymaga refaktoryzacji
- ❌ `song_edit.html` — 120 linii JS dla dynamicznych formularzy
- ❌ `song.html` — 40 linii JS dla eksportu SysEx
- ❌ Partiale używają `onclick` zamiast HTMX
- ❌ Brak endpointów dla kaskadowych zależności (device → types → fields)

---

## Zalety i wady HTMX

### ✅ Zalety które wykorzystamy
| Zaleta | Jak wykorzystamy |
|--------|------------------|
| Mniej JS | Usunięcie 160 linii ręcznego JS |
| Server-side rendering | Jeden szablon Jinja2 (DRY) |
| Spójność | Ten sam HTML przy ładowaniu i dynamicznie |
| Prostsza walidacja | Tylko Python, bez duplikacji |
| Progressive enhancement | Formularz działa bez JS (submit) |

### ⚠️ Wady których unikniemy
| Wada | Jak unikniemy |
|------|---------------|
| Latency (czekanie na serwer) | `hx-indicator` dla loading states |
| Za dużo requestów | Grupowanie operacji, minimalizacja |
| Utrata stanu formularza | Serwer zwraca formularz z danymi |
| Trudniejszy debugging | HTMX debug mode (`htmx.logAll()`) |
| Brak offline | Akceptowalne — app wymaga serwera MIDI |

---

## Plan implementacji

### Faza 1: Infrastruktura

- [ ] **1.1** Dodać endpoint `/partials/action-types` (kaskada device → types)
- [ ] **1.2** Dodać endpoint `/partials/action-fields` (kaskada type → fields)
- [ ] **1.3** Dodać testy dla nowych endpointów partiali
- [ ] **1.4** Uruchomić istniejące testy — upewnić się że przechodzą

### Faza 2: Partiale HTMX

- [ ] **2.1** `pacer_button.html` — zamienić `onclick` na `hx-delete` (usuwanie przycisku)
- [ ] **2.2** `pacer_button.html` — zamienić `onclick` na `hx-get` (dodawanie akcji)
- [ ] **2.3** `action_row.html` — zamienić `onclick` na `hx-delete` (usuwanie akcji)
- [ ] **2.4** `action_row.html` — zamienić `onchange` na `hx-get` (device → types)
- [ ] **2.5** `action_row.html` — zamienić `onchange` na `hx-get` (type → fields)
- [ ] **2.6** Dodać `hx-indicator` dla loading states

### Faza 3: song_edit.html

- [ ] **3.1** Zamienić "Dodaj przycisk" na `hx-get="/partials/pacer-button"`
- [ ] **3.2** Dodać walidację limitu 6 przycisków (server-side)
- [ ] **3.3** Usunąć funkcje JS: `createButtonCard`, `addAction`
- [ ] **3.4** Usunąć funkcje JS: `updateActionTypes`, `updateActionFields`
- [ ] **3.5** Przetestować edycję istniejącego utworu
- [ ] **3.6** Przetestować tworzenie nowego utworu

### Faza 4: song.html (eksport SysEx)

- [ ] **4.1** Zamienić `fetch()` na `hx-post` dla "Wyślij do Pacer"
- [ ] **4.2** Zamienić event listener na `hx-get` dla dynamicznego linku download
- [ ] **4.3** Dodać `hx-swap="innerHTML"` dla `#send-result`
- [ ] **4.4** Usunąć cały blok `<script>` z song.html

### Faza 5: Walidacja i cleanup

- [ ] **5.1** Uruchomić wszystkie testy (`uv run pytest`)
- [ ] **5.2** Testy E2E dla formularza edycji
- [ ] **5.3** Testy E2E dla eksportu SysEx
- [ ] **5.4** Usunąć nieużywany kod JS z song_edit.html
- [ ] **5.5** Usunąć `devices_json` z kontekstu (niepotrzebne)
- [ ] **5.6** Code review — sprawdzić czy nie ma duplikacji

---

## Nowe endpointy (Faza 1)

### GET /partials/action-types
```python
@router.get("/partials/action-types", response_class=HTMLResponse)
async def get_action_types(request: Request, device_id: str, button_idx: int, action_idx: int):
    """Return action type options for selected device."""
    # Zwraca <option> dla selecta typów akcji
```

### GET /partials/action-fields
```python
@router.get("/partials/action-fields", response_class=HTMLResponse)
async def get_action_fields(request: Request, action_type: str, button_idx: int, action_idx: int):
    """Return input fields for selected action type."""
    # Zwraca inputy (value, cc, label) dla wybranego typu
```

---

## Wzorce HTMX do użycia

### Dodawanie elementów
```html
<button hx-get="/partials/pacer-button?button_idx=0"
        hx-target="#pacer-buttons"
        hx-swap="beforeend"
        hx-indicator="#loading">
    + Dodaj przycisk
</button>
```

### Usuwanie elementów
```html
<button hx-delete="javascript:void(0)"
        hx-target="closest .pacer-button-card"
        hx-swap="outerHTML"
        hx-confirm="Usunąć przycisk?">
    🗑️
</button>
```

Uwaga: Usuwanie jest client-side (HTMX `remove`), nie wymaga requestu.

### Kaskadowe selecty
```html
<select hx-get="/partials/action-types"
        hx-target="next .action-type-select"
        hx-swap="innerHTML"
        hx-include="this"
        hx-trigger="change"
        name="device_id">
```

### Loading indicator
```html
<div id="loading" class="htmx-indicator">
    <span class="animate-spin">⏳</span>
</div>
```

---

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja |
|--------|-------------------|-------|-----------|
| Regresja formularzy | Średnie | Wysoki | Testy E2E przed i po |
| Konflikt indeksów button/action | Średnie | Średni | Server-side walidacja kolejności |
| Latency przy wielu klikach | Niskie | Niski | hx-disable podczas requestu |

---

## Definition of Done

1. ✅ Wszystkie testy przechodzą
2. ✅ Brak inline JavaScript w szablonach (z wyjątkiem htmx config)
3. ✅ Formularze działają identycznie jak przed refaktoryzacją
4. ✅ Loading indicators widoczne przy operacjach
5. ✅ Code review zakończony

---

## Notatki implementacyjne

### HTMX Extensions do rozważenia
- `hx-ext="remove-me"` — dla animacji usuwania
- `hx-ext="loading-states"` — dla zaawansowanych loading states

### Debugging
```javascript
// Włącz w konsoli przeglądarki
htmx.logAll();
```

### Fallback bez JS
Formularz powinien działać jako zwykły POST nawet bez HTMX (progressive enhancement).
