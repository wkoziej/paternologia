# ABOUTME: Unit tests for Pacer SysEx export.
# ABOUTME: Tests export_song_to_syx function with various song configurations.

import pytest

from paternologia.models import (
    Action,
    ActionType,
    Device,
    PacerButton,
    Song,
    SongMetadata,
)
from paternologia.pacer.export import export_song_to_syx
from paternologia.pacer import constants as c


@pytest.fixture
def devices():
    """Sample devices for testing."""
    return [
        Device(id="boss", name="Boss RC-600", midi_channel=0),
        Device(id="ms", name="Elektron M:S", midi_channel=1),
        Device(id="freak", name="MicroFreak", midi_channel=2),
    ]


class TestExportBasic:
    """Basic export tests."""

    def test_export_minimal_song(self, devices):
        """Export minimal song (no buttons)."""
        song = Song(
            song=SongMetadata(id="test", name="TEST"),
            pacer=[]
        )
        syx = export_song_to_syx(song, devices, "A1")

        assert len(syx) > 0
        assert syx[0] == c.SYSEX_START
        # Find first F7 (end of first message)
        assert c.SYSEX_END in syx

    def test_export_contains_preset_name(self, devices):
        """Exported data contains preset name."""
        song = Song(
            song=SongMetadata(id="test", name="TESTSONG"),
            pacer=[]
        )
        syx = export_song_to_syx(song, devices, "A1")

        assert b"TESTSONG" in syx

    def test_export_different_preset(self, devices):
        """Different target preset affects output."""
        song = Song(
            song=SongMetadata(id="test", name="X"),
            pacer=[]
        )
        syx_a1 = export_song_to_syx(song, devices, "A1")
        syx_b3 = export_song_to_syx(song, devices, "B3")

        # Different preset indices in the data
        assert syx_a1 != syx_b3


class TestExportWithButtons:
    """Export tests with PACER buttons."""

    def test_export_single_button(self, devices):
        """Export song with one button."""
        song = Song(
            song=SongMetadata(id="test", name="TEST"),
            pacer=[
                PacerButton(
                    name="Start",
                    actions=[
                        Action(device="boss", type=ActionType.PRESET, value=1)
                    ]
                )
            ]
        )
        syx = export_song_to_syx(song, devices, "A1")

        # Should have preset name + 6 control modes + 36 control steps + 36 LED configs
        # Count F0...F7 pairs
        f0_count = syx.count(bytes([c.SYSEX_START]))
        assert f0_count == 79  # 1 name + 6 control_mode + 36 steps + 36 LED

    def test_export_multiple_actions(self, devices):
        """Export button with multiple actions."""
        song = Song(
            song=SongMetadata(id="test", name="TEST"),
            pacer=[
                PacerButton(
                    name="Complex",
                    actions=[
                        Action(device="boss", type=ActionType.PRESET, value=1),
                        Action(device="ms", type=ActionType.PATTERN, value="A01"),
                        Action(device="freak", type=ActionType.PRESET, value=65),
                    ]
                )
            ]
        )
        syx = export_song_to_syx(song, devices, "A1")

        # Verify MSG_SW_PRG_STEP (0x46) appears multiple times
        assert syx.count(bytes([c.MSG_SW_PRG_STEP])) >= 3


class TestExportEmptySteps:
    """Tests for empty/inactive step handling."""

    def test_empty_button_clears_steps(self, devices):
        """Empty song generates MSG_CTRL_OFF for all steps."""
        song = Song(
            song=SongMetadata(id="empty", name="Empty"),
            pacer=[]
        )
        syx = export_song_to_syx(song, devices, "A1")

        # All 36 steps should have MSG_CTRL_OFF (0x61)
        # Count may be slightly higher due to checksums that happen to equal 0x61
        ctrl_off_count = syx.count(bytes([c.MSG_CTRL_OFF]))
        assert ctrl_off_count >= 36

    def test_partial_button_clears_remaining(self, devices):
        """Button with 2 actions clears remaining 4 steps."""
        song = Song(
            song=SongMetadata(id="px", name="PX"),  # No 'a' in name to avoid MSG_CTRL_OFF collision
            pacer=[
                PacerButton(
                    name="Btn",
                    actions=[
                        Action(device="boss", type=ActionType.PRESET, value=1),
                        Action(device="boss", type=ActionType.PRESET, value=2),
                    ]
                )
            ]
        )
        syx = export_song_to_syx(song, devices, "A1")

        # Button 1: 2 active + 4 inactive
        # Buttons 2-6: 6 inactive each = 30
        # Total inactive: 4 + 30 = 34
        assert syx.count(bytes([c.MSG_CTRL_OFF])) == 34


class TestExportSysExFormat:
    """Tests for correct SysEx format."""

    def test_all_messages_valid_sysex(self, devices):
        """All messages start with F0 and end with F7."""
        song = Song(
            song=SongMetadata(id="test", name="TEST"),
            pacer=[
                PacerButton(
                    name="Btn",
                    actions=[Action(device="boss", type=ActionType.PRESET, value=1)]
                )
            ]
        )
        syx = export_song_to_syx(song, devices, "A1")

        # Split into messages
        messages = []
        start = 0
        for i, b in enumerate(syx):
            if b == c.SYSEX_END:
                messages.append(syx[start:i+1])
                start = i + 1

        for msg in messages:
            assert msg[0] == c.SYSEX_START
            assert msg[-1] == c.SYSEX_END
            # Manufacturer ID
            assert msg[1:4] == c.MANUFACTURER_ID

    def test_messages_concatenated(self, devices):
        """Messages are directly concatenated without separators."""
        song = Song(
            song=SongMetadata(id="x", name="X"),
            pacer=[]
        )
        syx = export_song_to_syx(song, devices, "A1")

        # After each F7, next byte should be F0 (or end of data)
        for i, b in enumerate(syx[:-1]):
            if b == c.SYSEX_END:
                assert syx[i+1] == c.SYSEX_START
