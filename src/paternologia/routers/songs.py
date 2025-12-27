# ABOUTME: Songs API router for Paternologia.
# ABOUTME: Provides CRUD endpoints for song configurations with HTMX support.

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from paternologia.dependencies import get_storage, get_templates
from paternologia.models import (
    Action,
    ActionType,
    PacerButton,
    PacerExportSettings,
    Song,
    SongMetadata,
)

router = APIRouter(tags=["songs"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page - list all songs."""
    storage = get_storage()
    templates = get_templates()
    songs = storage.get_songs()
    devices = storage.get_devices()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"songs": songs, "devices": devices},
    )


@router.get("/songs/new", response_class=HTMLResponse)
async def new_song(request: Request):
    """Form for creating a new song."""
    storage = get_storage()
    templates = get_templates()
    devices = storage.get_devices()
    devices_json = [d.model_dump(mode="json") for d in devices]

    return templates.TemplateResponse(
        request=request,
        name="song_edit.html",
        context={"song": None, "devices": devices, "devices_json": devices_json, "is_new": True},
    )


@router.get("/songs/{song_id}", response_class=HTMLResponse)
async def view_song(request: Request, song_id: str):
    """View a song's PACER configuration."""
    storage = get_storage()
    templates = get_templates()
    song = storage.get_song(song_id)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    devices = storage.get_devices()
    devices_map = {d.id: d for d in devices}

    return templates.TemplateResponse(
        request=request,
        name="song.html",
        context={"song": song, "devices": devices, "devices_map": devices_map},
    )


@router.get("/songs/{song_id}/edit", response_class=HTMLResponse)
async def edit_song(request: Request, song_id: str):
    """Form for editing a song."""
    storage = get_storage()
    templates = get_templates()
    song = storage.get_song(song_id)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    devices = storage.get_devices()
    devices_json = [d.model_dump(mode="json") for d in devices]

    return templates.TemplateResponse(
        request=request,
        name="song_edit.html",
        context={"song": song, "devices": devices, "devices_json": devices_json, "is_new": False},
    )


@router.post("/songs", response_class=HTMLResponse)
async def create_song(request: Request):
    """Create a new song from form data."""
    storage = get_storage()
    form_data = await request.form()

    song_id = form_data.get("song_id", "").strip()
    song_name = form_data.get("song_name", "").strip()
    song_author = form_data.get("song_author", "").strip()
    song_notes = form_data.get("song_notes", "").strip()

    if not song_id or not song_name:
        raise HTTPException(status_code=400, detail="ID and name are required")

    if storage.song_exists(song_id):
        raise HTTPException(status_code=400, detail="Song with this ID already exists")

    song = _build_song_from_form(form_data, song_id, song_name, song_author, song_notes, storage)
    storage.save_song(song)

    return RedirectResponse(url=f"/songs/{song_id}", status_code=303)


@router.put("/songs/{song_id}", response_class=HTMLResponse)
async def update_song(request: Request, song_id: str):
    """Update an existing song from form data."""
    storage = get_storage()

    if not storage.song_exists(song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    form_data = await request.form()
    song_name = form_data.get("song_name", "").strip()
    song_author = form_data.get("song_author", "").strip()
    song_notes = form_data.get("song_notes", "").strip()

    if not song_name:
        raise HTTPException(status_code=400, detail="Name is required")

    song = _build_song_from_form(form_data, song_id, song_name, song_author, song_notes, storage)
    storage.save_song(song)

    return RedirectResponse(url=f"/songs/{song_id}", status_code=303)


@router.delete("/songs/{song_id}")
async def delete_song(song_id: str):
    """Delete a song."""
    storage = get_storage()

    if not storage.delete_song(song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    return RedirectResponse(url="/", status_code=303)


def _build_song_from_form(
    form_data,
    song_id: str,
    song_name: str,
    song_author: str,
    song_notes: str,
    storage,
) -> Song:
    """Build a Song model from form data."""
    devices = storage.get_devices()
    device_ids = [d.id for d in devices]

    target_preset = form_data.get("pacer_export_target_preset", "A1").strip()
    pacer_export = PacerExportSettings(target_preset=target_preset or "A1")

    pacer_buttons = []
    button_idx = 0

    while True:
        button_name = form_data.get(f"button_{button_idx}_name", "").strip()
        if not button_name and button_idx > 0:
            break

        if button_name:
            actions = []
            action_idx = 0

            while True:
                action_device = form_data.get(f"button_{button_idx}_action_{action_idx}_device", "").strip()
                if not action_device:
                    break

                action_type_str = form_data.get(f"button_{button_idx}_action_{action_idx}_type", "").strip()
                action_value = form_data.get(f"button_{button_idx}_action_{action_idx}_value", "").strip()
                action_cc = form_data.get(f"button_{button_idx}_action_{action_idx}_cc", "").strip()
                action_label = form_data.get(f"button_{button_idx}_action_{action_idx}_label", "").strip()

                if action_type_str:
                    action_type = ActionType(action_type_str)

                    value = None
                    if action_value:
                        if action_type == ActionType.PATTERN:
                            value = action_value
                        else:
                            value = int(action_value)

                    action = Action(
                        device=action_device,
                        type=action_type,
                        value=value,
                        cc=int(action_cc) if action_cc else None,
                        label=action_label or None,
                    )
                    actions.append(action)

                action_idx += 1
                if action_idx > 6:
                    break

            pacer_buttons.append(PacerButton(name=button_name, actions=actions))

        button_idx += 1
        if button_idx > 6:
            break

    return Song(
        song=SongMetadata(
            id=song_id,
            name=song_name,
            author=song_author,
            created=date.today(),
            notes=song_notes,
            pacer_export=pacer_export,
        ),
        pacer=pacer_buttons,
    )


@router.get("/partials/action-row", response_class=HTMLResponse)
async def get_action_row(request: Request, button_idx: int, action_idx: int):
    """Return a new action row partial for HTMX."""
    storage = get_storage()
    templates = get_templates()
    devices = storage.get_devices()

    return templates.TemplateResponse(
        request=request,
        name="partials/action_row.html",
        context={
            "button_idx": button_idx,
            "action_idx": action_idx,
            "action": None,
            "devices": devices,
        },
    )


@router.get("/partials/pacer-button", response_class=HTMLResponse)
async def get_pacer_button(request: Request, button_idx: int):
    """Return a new PACER button partial for HTMX."""
    storage = get_storage()
    templates = get_templates()
    devices = storage.get_devices()

    return templates.TemplateResponse(
        request=request,
        name="partials/pacer_button.html",
        context={
            "button_idx": button_idx,
            "button": None,
            "devices": devices,
            "is_edit": True,
        },
    )


@router.get("/partials/action-types", response_class=HTMLResponse)
async def get_action_types(
    request: Request, device_id: str, button_idx: int, action_idx: int
):
    """Return action type options for selected device (HTMX cascade)."""
    storage = get_storage()
    templates = get_templates()
    devices = storage.get_devices()

    device = next((d for d in devices if d.id == device_id), None)
    action_types = device.action_types if device else []

    return templates.TemplateResponse(
        request=request,
        name="partials/action_types.html",
        context={
            "button_idx": button_idx,
            "action_idx": action_idx,
            "action_types": action_types,
        },
    )


@router.get("/partials/action-fields", response_class=HTMLResponse)
async def get_action_fields(
    request: Request, action_type: str, button_idx: int, action_idx: int
):
    """Return input fields for selected action type (HTMX cascade)."""
    templates = get_templates()

    return templates.TemplateResponse(
        request=request,
        name="partials/action_fields.html",
        context={
            "button_idx": button_idx,
            "action_idx": action_idx,
            "action_type": action_type,
            "action": None,
        },
    )
