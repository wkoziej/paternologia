# ABOUTME: FastAPI router for Pacer SysEx export and send endpoints.
# ABOUTME: Provides GET /pacer/export/{song_id}.syx and POST /pacer/send/{song_id}.

import subprocess
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response

from ..dependencies import get_storage
from ..models import VALID_PRESETS
from ..storage import Storage
from ..pacer.export import export_song_to_syx
from ..pacer import constants as c

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
    song_id: str,
    preset: str | None = None,
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
        raise HTTPException(400, "Missing amidi port configuration in data/pacer.yaml")

    port = pacer_config.amidi_port
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

    return {"status": "ok", "preset": target, "port": port}
