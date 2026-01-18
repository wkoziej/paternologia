# ABOUTME: FastAPI router for Pacer SysEx export and send endpoints.
# ABOUTME: Provides GET /pacer/export/{song_id}.syx and POST /pacer/send/{song_id}.

import subprocess
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import Response, HTMLResponse

from ..dependencies import get_storage
from ..models import VALID_PRESETS
from ..storage import Storage
from ..pacer.export import export_song_to_syx
from ..pacer import constants as c

router = APIRouter(prefix="/pacer", tags=["pacer"])


def find_midi_port(device_name: str) -> str | None:
    """Znajdź port amidi po nazwie urządzenia.

    Args:
        device_name: Fragment nazwy urządzenia (np. "PACER")

    Returns:
        Port w formacie hw:X,Y,Z lub None jeśli nie znaleziono
    """
    try:
        result = subprocess.run(
            ["amidi", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.strip().split("\n"):
            if device_name.upper() in line.upper():
                # Format: "IO  hw:4,0,0  PACER MIDI1"
                parts = line.split()
                if len(parts) >= 2 and parts[1].startswith("hw:"):
                    return parts[1]
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


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
        raise HTTPException(400, f"Invalid preset: {preset}. Valid: CURRENT, A1-D6.")

    # Pobierz devices do mapowania MIDI channels
    devices = storage.get_devices()

    syx_data = export_song_to_syx(song, devices, preset)

    return Response(
        content=syx_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{song_id}_{preset}.syx"'
        }
    )


@router.post("/send/{song_id}")
def send_to_pacer(
    request: Request,
    song_id: str,
    preset: str | None = Form(None),
    storage: Storage = Depends(get_storage)
):
    """Wyślij piosenkę do Pacera przez amidi."""
    song = storage.get_song(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    target = preset or song.song.pacer_export.target_preset
    target = target.upper()

    if target not in VALID_PRESETS:
        raise HTTPException(400, f"Invalid preset: {target}. Valid: A1-D6.")

    pacer_config = storage.get_pacer_config()
    if not pacer_config:
        raise HTTPException(400, "Missing configuration in data/pacer.yaml")

    # Auto-detekcja portu po nazwie urządzenia
    port = find_midi_port(pacer_config.device_name)
    if not port:
        raise HTTPException(
            400,
            f"Nie znaleziono urządzenia '{pacer_config.device_name}'. "
            "Sprawdź połączenie i uruchom 'amidi -l'."
        )

    timeout_seconds = pacer_config.amidi_timeout_seconds
    sysex_interval = pacer_config.sysex_interval_ms

    devices = storage.get_devices()
    syx_data = export_song_to_syx(song, devices, target)

    try:
        with NamedTemporaryFile(suffix=".syx", delete=True) as tmp:
            tmp.write(syx_data)
            tmp.flush()
            # CRITICAL: --sysex-interval is required for reliable transfer!
            run = subprocess.run(
                ["amidi", "-p", port, f"--sysex-interval={sysex_interval}", "-s", tmp.name],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
    except FileNotFoundError:
        raise HTTPException(500, "amidi not found - install alsa-utils package")

    if run.returncode != 0:
        raise HTTPException(500, f"amidi failed: {run.stderr.strip()}")

    # Return HTML for HTMX requests, JSON for API clients
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return HTMLResponse(
            f'<span class="text-green-600">Wysłano do preset {target} na port {port}</span>'
        )

    return {"status": "ok", "preset": target, "port": port}
