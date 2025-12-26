# ABOUTME: Unit tests for Pydantic models.
# ABOUTME: Tests Device, Action, PacerButton, DeviceSettings, and Song validation.

from datetime import date

import pytest
from pydantic import ValidationError

from paternologia.models import (
    Action,
    ActionType,
    Device,
    DevicesConfig,
    PacerButton,
    Song,
    SongMetadata,
)


class TestDevice:
    """Tests for Device model."""

    def test_device_creation_minimal(self):
        """Device can be created with just id and name."""
        device = Device(id="boss", name="Boss RC-600")
        assert device.id == "boss"
        assert device.name == "Boss RC-600"
        assert device.description == ""
        assert device.action_types == []

    def test_device_creation_full(self):
        """Device can be created with all fields."""
        device = Device(
            id="boss",
            name="Boss RC-600",
            description="Loop Station",
            action_types=[ActionType.PRESET, ActionType.CC],
        )
        assert device.description == "Loop Station"
        assert ActionType.PRESET in device.action_types
        assert ActionType.CC in device.action_types

    def test_device_requires_id(self):
        """Device requires id field."""
        with pytest.raises(ValidationError):
            Device(name="Test")

    def test_device_requires_name(self):
        """Device requires name field."""
        with pytest.raises(ValidationError):
            Device(id="test")


class TestDevicesConfig:
    """Tests for DevicesConfig model."""

    def test_empty_config(self):
        """DevicesConfig can be empty."""
        config = DevicesConfig()
        assert config.devices == []

    def test_config_with_devices(self):
        """DevicesConfig can contain multiple devices."""
        config = DevicesConfig(
            devices=[
                Device(id="boss", name="Boss"),
                Device(id="freak", name="Freak"),
            ]
        )
        assert len(config.devices) == 2


class TestAction:
    """Tests for Action model."""

    def test_preset_action(self):
        """Preset action with value and label."""
        action = Action(
            device="boss",
            type=ActionType.PRESET,
            value=1,
            label="W ciszy",
        )
        assert action.device == "boss"
        assert action.type == ActionType.PRESET
        assert action.value == 1
        assert action.label == "W ciszy"

    def test_pattern_action(self):
        """Pattern action with string value."""
        action = Action(
            device="ms",
            type=ActionType.PATTERN,
            value="A0",
        )
        assert action.value == "A0"

    def test_cc_action(self):
        """CC action with cc number and value."""
        action = Action(
            device="boss",
            type=ActionType.CC,
            cc=1,
            value=127,
            label="Play/Rec",
        )
        assert action.cc == 1
        assert action.value == 127
        assert action.label == "Play/Rec"

    def test_action_requires_device(self):
        """Action requires device field."""
        with pytest.raises(ValidationError):
            Action(type=ActionType.PRESET, value=1)

    def test_action_requires_type(self):
        """Action requires type field."""
        with pytest.raises(ValidationError):
            Action(device="boss", value=1)


class TestPacerButton:
    """Tests for PacerButton model."""

    def test_button_with_actions(self):
        """Button can have multiple actions."""
        button = PacerButton(
            name="Start",
            actions=[
                Action(device="boss", type=ActionType.PRESET, value=1),
                Action(device="ms", type=ActionType.PATTERN, value="A0"),
            ],
        )
        assert button.name == "Start"
        assert len(button.actions) == 2

    def test_button_max_six_actions(self):
        """Button can have at most 6 actions."""
        actions = [
            Action(device="boss", type=ActionType.PRESET, value=i) for i in range(7)
        ]
        with pytest.raises(ValidationError):
            PacerButton(name="Too Many", actions=actions)

    def test_button_empty_actions(self):
        """Button can have no actions."""
        button = PacerButton(name="Empty")
        assert button.actions == []


class TestSongMetadata:
    """Tests for SongMetadata model."""

    def test_metadata_minimal(self):
        """Metadata with required fields only."""
        meta = SongMetadata(id="w-ciszy", name="W ciszy")
        assert meta.id == "w-ciszy"
        assert meta.name == "W ciszy"
        assert meta.author == ""
        assert meta.notes == ""
        assert meta.created == date.today()

    def test_metadata_full(self):
        """Metadata with all fields."""
        meta = SongMetadata(
            id="w-ciszy",
            name="W ciszy",
            author="Wojtek",
            created=date(2024, 12, 14),
            notes="Ballada, tempo 72 BPM",
        )
        assert meta.author == "Wojtek"
        assert meta.created == date(2024, 12, 14)


class TestSong:
    """Tests for Song model."""

    def test_song_minimal(self):
        """Song with minimal data."""
        song = Song(song=SongMetadata(id="test", name="Test"))
        assert song.song.id == "test"
        assert song.pacer == []

    def test_song_full(self):
        """Song with all components."""
        song = Song(
            song=SongMetadata(
                id="w-ciszy",
                name="W ciszy",
                author="Wojtek",
                created=date(2024, 12, 14),
            ),
            pacer=[
                PacerButton(
                    name="Start",
                    actions=[
                        Action(device="boss", type=ActionType.PRESET, value=1),
                    ],
                ),
            ],
        )
        assert len(song.pacer) == 1

    def test_song_max_six_pacer_buttons(self):
        """Song can have at most 6 PACER buttons."""
        buttons = [PacerButton(name=f"Button {i}") for i in range(7)]
        with pytest.raises(ValidationError):
            Song(
                song=SongMetadata(id="test", name="Test"),
                pacer=buttons,
            )
