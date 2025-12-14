# ABOUTME: YAML-based storage layer for Paternologia devices and songs.
# ABOUTME: Handles reading/writing device configs and song files from data/ directory.

from pathlib import Path

import yaml

from paternologia.models import Device, DevicesConfig, Song, SongMetadata


class Storage:
    """YAML file storage for devices and songs."""

    def __init__(self, data_dir: Path | str = "data"):
        self.data_dir = Path(data_dir)
        self.devices_file = self.data_dir / "devices.yaml"
        self.songs_dir = self.data_dir / "songs"

    def _ensure_dirs(self) -> None:
        """Ensure data directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.songs_dir.mkdir(parents=True, exist_ok=True)

    def get_devices(self) -> list[Device]:
        """Load all devices from devices.yaml."""
        if not self.devices_file.exists():
            return []

        with open(self.devices_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = DevicesConfig.model_validate(data)
        return config.devices

    def get_device(self, device_id: str) -> Device | None:
        """Get a single device by ID."""
        devices = self.get_devices()
        for device in devices:
            if device.id == device_id:
                return device
        return None

    def save_devices(self, devices: list[Device]) -> None:
        """Save devices to devices.yaml."""
        self._ensure_dirs()
        config = DevicesConfig(devices=devices)
        data = config.model_dump(mode="json")

        with open(self.devices_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def get_songs(self) -> list[Song]:
        """Load all songs from songs/ directory."""
        if not self.songs_dir.exists():
            return []

        songs = []
        for song_file in sorted(self.songs_dir.glob("*.yaml")):
            song = self._load_song_file(song_file)
            if song:
                songs.append(song)

        return songs

    def get_song(self, song_id: str) -> Song | None:
        """Load a single song by ID."""
        song_file = self.songs_dir / f"{song_id}.yaml"
        if not song_file.exists():
            return None

        return self._load_song_file(song_file)

    def _load_song_file(self, song_file: Path) -> Song | None:
        """Load and parse a song YAML file."""
        with open(song_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if not data:
            return None

        return Song.model_validate(data)

    def save_song(self, song: Song) -> None:
        """Save a song to its YAML file."""
        self._ensure_dirs()
        song_file = self.songs_dir / f"{song.song.id}.yaml"
        data = song.model_dump(mode="json")

        with open(song_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def delete_song(self, song_id: str) -> bool:
        """Delete a song file. Returns True if deleted, False if not found."""
        song_file = self.songs_dir / f"{song_id}.yaml"
        if not song_file.exists():
            return False

        song_file.unlink()
        return True

    def song_exists(self, song_id: str) -> bool:
        """Check if a song with given ID exists."""
        song_file = self.songs_dir / f"{song_id}.yaml"
        return song_file.exists()
