# ABOUTME: FastAPI router for Pacer SysEx export endpoint.
# ABOUTME: Provides GET /pacer/export/{song_id}.syx for downloading .syx files.

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response

from ..dependencies import get_storage
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
