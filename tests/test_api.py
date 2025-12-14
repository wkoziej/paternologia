# ABOUTME: Integration tests for Paternologia API endpoints.
# ABOUTME: Tests songs CRUD and devices endpoints using FastAPI TestClient.

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paternologia import dependencies
from paternologia.main import app
from paternologia.models import ActionType, Device
from paternologia.storage import Storage


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_storage(temp_data_dir):
    """Create storage with temporary directory."""
    storage = Storage(data_dir=temp_data_dir)
    storage._ensure_dirs()
    return storage


@pytest.fixture
def sample_devices(test_storage):
    """Create sample devices in storage."""
    devices = [
        Device(
            id="boss",
            name="Boss RC-600",
            description="Loop Station",
            action_types=[ActionType.PRESET, ActionType.CC],
        ),
        Device(
            id="ms",
            name="Elektron Model:Samples",
            description="Sampler/Sequencer",
            action_types=[ActionType.PATTERN],
        ),
    ]
    test_storage.save_devices(devices)
    return devices


@pytest.fixture
def client(test_storage, temp_data_dir):
    """Create test client with mocked storage."""
    original_get_storage = dependencies.get_storage
    original_templates = dependencies._templates

    dependencies._storage = test_storage
    dependencies._templates = None
    dependencies.TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
    dependencies.DATA_DIR = temp_data_dir

    with TestClient(app) as client:
        yield client

    dependencies._storage = None
    dependencies._templates = original_templates


class TestIndexPage:
    """Tests for main index page."""

    def test_index_empty(self, client, sample_devices):
        """Index page shows empty message when no songs."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Brak utworów" in response.text

    def test_index_with_songs(self, client, sample_devices, test_storage):
        """Index page lists songs."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        response = client.get("/")
        assert response.status_code == 200
        assert "Test Song" in response.text


class TestDevicesEndpoints:
    """Tests for devices API endpoints."""

    def test_devices_page(self, client, sample_devices):
        """Devices page lists all devices."""
        response = client.get("/devices")
        assert response.status_code == 200
        assert "Boss RC-600" in response.text
        assert "Elektron Model:Samples" in response.text

    def test_devices_json(self, client, sample_devices):
        """API returns devices as JSON."""
        response = client.get("/api/devices")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "boss"
        assert data[1]["id"] == "ms"


class TestSongView:
    """Tests for song view page."""

    def test_view_song_not_found(self, client, sample_devices):
        """Returns 404 for nonexistent song."""
        response = client.get("/songs/nonexistent")
        assert response.status_code == 404

    def test_view_song(self, client, sample_devices, test_storage):
        """View page shows song details."""
        from paternologia.models import DeviceSettings, Song, SongMetadata

        song = Song(
            song=SongMetadata(id="test", name="Test Song", notes="Test notes"),
            devices={"boss": DeviceSettings(preset=1)},
        )
        test_storage.save_song(song)

        response = client.get("/songs/test")
        assert response.status_code == 200
        assert "Test Song" in response.text
        assert "Test notes" in response.text


class TestSongEdit:
    """Tests for song edit page."""

    def test_new_song_form(self, client, sample_devices):
        """New song form loads correctly."""
        response = client.get("/songs/new")
        assert response.status_code == 200
        assert "NOWY UTWÓR" in response.text

    def test_edit_song_form(self, client, sample_devices, test_storage):
        """Edit form loads with song data."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        response = client.get("/songs/test/edit")
        assert response.status_code == 200
        assert "Test Song" in response.text

    def test_edit_song_not_found(self, client, sample_devices):
        """Returns 404 for nonexistent song."""
        response = client.get("/songs/nonexistent/edit")
        assert response.status_code == 404


class TestSongCRUD:
    """Tests for song create/update/delete operations."""

    def test_create_song(self, client, sample_devices, test_storage):
        """Create a new song via POST."""
        response = client.post(
            "/songs",
            data={
                "song_id": "new-song",
                "song_name": "New Song",
                "song_author": "Test Author",
                "song_notes": "Test notes",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/songs/new-song"

        song = test_storage.get_song("new-song")
        assert song is not None
        assert song.song.name == "New Song"

    def test_create_song_missing_fields(self, client, sample_devices):
        """Create fails without required fields."""
        response = client.post(
            "/songs",
            data={"song_id": "", "song_name": ""},
        )
        assert response.status_code == 400

    def test_create_duplicate_song(self, client, sample_devices, test_storage):
        """Create fails for duplicate ID."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="existing", name="Existing"))
        test_storage.save_song(song)

        response = client.post(
            "/songs",
            data={"song_id": "existing", "song_name": "Duplicate"},
        )
        assert response.status_code == 400

    def test_update_song(self, client, sample_devices, test_storage):
        """Update an existing song via PUT."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Original"))
        test_storage.save_song(song)

        response = client.put(
            "/songs/test",
            data={
                "song_name": "Updated Name",
                "song_author": "New Author",
                "song_notes": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        updated = test_storage.get_song("test")
        assert updated.song.name == "Updated Name"

    def test_update_song_not_found(self, client, sample_devices):
        """Update fails for nonexistent song."""
        response = client.put(
            "/songs/nonexistent",
            data={"song_name": "Test"},
        )
        assert response.status_code == 404

    def test_delete_song(self, client, sample_devices, test_storage):
        """Delete a song via DELETE."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="to-delete", name="Delete Me"))
        test_storage.save_song(song)

        response = client.delete("/songs/to-delete", follow_redirects=False)
        assert response.status_code == 303

        assert not test_storage.song_exists("to-delete")

    def test_delete_song_not_found(self, client, sample_devices):
        """Delete fails for nonexistent song."""
        response = client.delete("/songs/nonexistent")
        assert response.status_code == 404


class TestSongWithPacerButtons:
    """Tests for creating songs with PACER button configurations."""

    def test_create_song_with_buttons(self, client, sample_devices, test_storage):
        """Create song with PACER buttons and actions."""
        response = client.post(
            "/songs",
            data={
                "song_id": "with-buttons",
                "song_name": "Song With Buttons",
                "song_author": "",
                "song_notes": "",
                "device_boss_preset": "5",
                "device_boss_preset_name": "Test Preset",
                "button_0_name": "Start",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "preset",
                "button_0_action_0_value": "5",
                "button_0_action_0_label": "Start preset",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("with-buttons")
        assert song is not None
        assert len(song.pacer) == 1
        assert song.pacer[0].name == "Start"
        assert len(song.pacer[0].actions) == 1
        assert song.pacer[0].actions[0].value == 5
