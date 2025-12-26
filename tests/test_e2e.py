# ABOUTME: End-to-end tests for Paternologia application.
# ABOUTME: Tests full user workflows from browsing to creating and managing songs.

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
def setup_devices(test_storage):
    """Setup standard devices for testing."""
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
        Device(
            id="freak",
            name="Arturia MicroFreak",
            description="Synthesizer",
            action_types=[ActionType.PRESET],
        ),
    ]
    test_storage.save_devices(devices)
    return devices


@pytest.fixture
def client(test_storage, temp_data_dir):
    """Create test client with mocked storage."""
    dependencies._storage = test_storage
    dependencies._templates = None
    dependencies.TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
    dependencies.DATA_DIR = temp_data_dir

    with TestClient(app) as client:
        yield client

    dependencies._storage = None
    dependencies._templates = None


class TestFullUserWorkflow:
    """E2E tests for complete user workflows."""

    def test_browse_empty_app(self, client, setup_devices):
        """User can browse empty app and see devices."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Brak utworów" in response.text
        assert "Nowy utwór" in response.text

        response = client.get("/devices")
        assert response.status_code == 200
        assert "Boss RC-600" in response.text
        assert "Elektron Model:Samples" in response.text
        assert "Arturia MicroFreak" in response.text

    def test_create_view_edit_delete_song(self, client, setup_devices, test_storage):
        """User can create, view, edit, and delete a song."""
        response = client.get("/songs/new")
        assert response.status_code == 200
        assert "NOWY UTWÓR" in response.text
        assert "Boss RC-600" in response.text

        response = client.post(
            "/songs",
            data={
                "song_id": "test-song",
                "song_name": "Test Song",
                "song_author": "Test Author",
                "song_notes": "Test notes here",
                "device_boss_preset": "5",
                "device_boss_preset_name": "My Preset",
                "device_ms_pattern": "B2",
                "button_0_name": "Intro",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "preset",
                "button_0_action_0_value": "5",
                "button_0_action_0_label": "Intro preset",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/songs/test-song"

        response = client.get("/songs/test-song")
        assert response.status_code == 200
        assert "Test Song" in response.text
        assert "Test notes here" in response.text
        assert "preset 5" in response.text.lower()
        assert "Intro" in response.text

        response = client.get("/")
        assert response.status_code == 200
        assert "Test Song" in response.text

        response = client.get("/songs/test-song/edit")
        assert response.status_code == 200
        assert "EDYCJA: Test Song" in response.text

        response = client.put(
            "/songs/test-song",
            data={
                "song_name": "Updated Song Name",
                "song_author": "New Author",
                "song_notes": "Updated notes",
                "device_boss_preset": "10",
                "device_boss_preset_name": "Updated Preset",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        response = client.get("/songs/test-song")
        assert response.status_code == 200
        assert "Updated Song Name" in response.text

        response = client.delete("/songs/test-song", follow_redirects=False)
        assert response.status_code == 303

        response = client.get("/songs/test-song")
        assert response.status_code == 404

        response = client.get("/")
        assert response.status_code == 200
        assert "Updated Song Name" not in response.text

    def test_create_song_with_multiple_pacer_buttons(self, client, setup_devices, test_storage):
        """User can create a song with multiple PACER buttons and actions."""
        response = client.post(
            "/songs",
            data={
                "song_id": "multi-button",
                "song_name": "Multi Button Song",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Verse",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "preset",
                "button_0_action_0_value": "1",
                "button_0_action_1_device": "ms",
                "button_0_action_1_type": "pattern",
                "button_0_action_1_value": "A0",
                "button_1_name": "Chorus",
                "button_1_action_0_device": "boss",
                "button_1_action_0_type": "cc",
                "button_1_action_0_cc": "2",
                "button_1_action_0_value": "127",
                "button_1_action_0_label": "Loop Start",
                "button_2_name": "Bridge",
                "button_2_action_0_device": "freak",
                "button_2_action_0_type": "preset",
                "button_2_action_0_value": "42",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("multi-button")
        assert song is not None
        assert len(song.pacer) == 3
        assert song.pacer[0].name == "Verse"
        assert len(song.pacer[0].actions) == 2
        assert song.pacer[1].name == "Chorus"
        assert song.pacer[1].actions[0].cc == 2
        assert song.pacer[2].name == "Bridge"

        response = client.get("/songs/multi-button")
        assert response.status_code == 200
        assert "3 przyciski" in response.text
        assert "Verse" in response.text
        assert "Chorus" in response.text
        assert "Bridge" in response.text


class TestNavigationFlow:
    """E2E tests for navigation between pages."""

    def test_navigation_links(self, client, setup_devices, test_storage):
        """All navigation links work correctly."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="nav-test", name="Navigation Test"))
        test_storage.save_song(song)

        response = client.get("/")
        assert response.status_code == 200
        assert 'href="/devices"' in response.text
        assert 'href="/songs/new"' in response.text

        response = client.get("/devices")
        assert response.status_code == 200
        assert 'href="/"' in response.text

        response = client.get("/songs/nav-test")
        assert response.status_code == 200
        assert 'href="/"' in response.text
        assert 'href="/songs/nav-test/edit"' in response.text

        response = client.get("/songs/nav-test/edit")
        assert response.status_code == 200
        assert 'href="/songs/nav-test"' in response.text


class TestErrorHandling:
    """E2E tests for error scenarios."""

    def test_404_for_nonexistent_song(self, client, setup_devices):
        """App returns 404 for nonexistent songs."""
        response = client.get("/songs/does-not-exist")
        assert response.status_code == 404

        response = client.get("/songs/does-not-exist/edit")
        assert response.status_code == 404

    def test_duplicate_song_id_rejected(self, client, setup_devices, test_storage):
        """App rejects duplicate song IDs."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="existing", name="Existing Song"))
        test_storage.save_song(song)

        response = client.post(
            "/songs",
            data={"song_id": "existing", "song_name": "Duplicate Attempt"},
        )
        assert response.status_code == 400

    def test_missing_required_fields(self, client, setup_devices):
        """App rejects forms with missing required fields."""
        response = client.post(
            "/songs",
            data={"song_id": "", "song_name": ""},
        )
        assert response.status_code == 400

        response = client.post(
            "/songs",
            data={"song_id": "valid-id", "song_name": ""},
        )
        assert response.status_code == 400


class TestAPIEndpoints:
    """E2E tests for API endpoints."""

    def test_devices_json_api(self, client, setup_devices):
        """JSON API returns proper device data."""
        response = client.get("/api/devices")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3

        boss = next(d for d in data if d["id"] == "boss")
        assert boss["name"] == "Boss RC-600"
        assert "preset" in boss["action_types"]
        assert "cc" in boss["action_types"]

        ms = next(d for d in data if d["id"] == "ms")
        assert "pattern" in ms["action_types"]
