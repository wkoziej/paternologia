# ABOUTME: Unit tests for Pacer MIDI mappings.
# ABOUTME: Tests device channel mapping and action to MIDI conversion.

import pytest

from paternologia.models import Action, ActionType, Device
from paternologia.pacer.mappings import (
    action_to_midi,
    build_device_channel_map,
    get_device_channel,
    pattern_to_program,
)
from paternologia.pacer import constants as c


class TestBuildDeviceChannelMap:
    """Tests for device channel map building."""

    def test_build_from_devices(self):
        """Builds map from Device.midi_channel."""
        devices = [
            Device(id="boss", name="Boss", midi_channel=0),
            Device(id="ms", name="M:S", midi_channel=1),
            Device(id="freak", name="Freak", midi_channel=2),
        ]
        channel_map = build_device_channel_map(devices)

        assert channel_map["boss"] == 0
        assert channel_map["ms"] == 1
        assert channel_map["freak"] == 2

    def test_empty_devices(self):
        """Empty device list gives empty map."""
        assert build_device_channel_map([]) == {}


class TestGetDeviceChannel:
    """Tests for device channel lookup."""

    def test_known_device(self):
        """Returns channel for known device."""
        channel_map = {"boss": 5, "ms": 10}
        assert get_device_channel("boss", channel_map) == 5
        assert get_device_channel("ms", channel_map) == 10

    def test_unknown_device_fallback(self):
        """Returns 0 for unknown device."""
        channel_map = {"boss": 5}
        assert get_device_channel("unknown", channel_map) == 0


class TestPatternToProgram:
    """Tests for pattern ID conversion."""

    def test_integer_passthrough(self):
        """Integer values pass through unchanged."""
        assert pattern_to_program(42) == 42

    def test_pattern_a01(self):
        """A01 converts to 0."""
        assert pattern_to_program("A01") == 0

    def test_pattern_a16(self):
        """A16 converts to 15."""
        assert pattern_to_program("A16") == 15

    def test_pattern_b01(self):
        """B01 converts to 16."""
        assert pattern_to_program("B01") == 16

    def test_pattern_f16(self):
        """F16 converts to 95."""
        assert pattern_to_program("F16") == 95

    def test_lowercase_pattern(self):
        """Lowercase pattern letters work."""
        assert pattern_to_program("a01") == 0
        assert pattern_to_program("b02") == 17

    def test_invalid_pattern_fallback(self):
        """Invalid patterns return 0."""
        assert pattern_to_program("invalid") == 0
        assert pattern_to_program("X99") == 0
        assert pattern_to_program(None) == 0


class TestActionToMidiPreset:
    """Tests for PRESET action conversion."""

    def test_preset_basic(self):
        """PRESET action converts to MSG_SW_PRG_STEP."""
        action = Action(device="boss", type=ActionType.PRESET, value=5)
        channel_map = {"boss": 0}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert msg_type == c.MSG_SW_PRG_STEP
        assert channel == 0
        assert data1 == 0  # unused
        assert data2 == 5  # start (program)
        assert data3 == 5  # end (same = immediate)

    def test_preset_different_channel(self):
        """PRESET action on different channel."""
        action = Action(device="boss", type=ActionType.PRESET, value=10)
        channel_map = {"boss": 3}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert channel == 3
        assert data1 == 0  # unused
        assert data2 == 10  # start (program)
        assert data3 == 10  # end (same = immediate)


class TestActionToMidiPattern:
    """Tests for PATTERN action conversion."""

    def test_pattern_string(self):
        """PATTERN with string value."""
        action = Action(device="ms", type=ActionType.PATTERN, value="A02")
        channel_map = {"ms": 1}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert msg_type == c.MSG_SW_PRG_STEP
        assert channel == 1
        assert data1 == 0  # unused
        assert data2 == 1  # A02 = 1
        assert data3 == 1  # same = immediate

    def test_pattern_integer(self):
        """PATTERN with integer value."""
        action = Action(device="ms", type=ActionType.PATTERN, value=50)
        channel_map = {"ms": 1}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert data1 == 0  # unused
        assert data2 == 50  # start (program)
        assert data3 == 50  # end (same = immediate)


class TestActionToMidiCC:
    """Tests for CC action conversion."""

    def test_cc_action(self):
        """CC action converts to MSG_SW_MIDI_CC_TGGLE (toggle 127/0)."""
        action = Action(device="boss", type=ActionType.CC, cc=74, value=127)
        channel_map = {"boss": 0}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert msg_type == c.MSG_SW_MIDI_CC_TGGLE
        assert channel == 0
        assert data1 == 74  # CC number
        assert data2 == 127  # value1 (ON)
        assert data3 == 0    # value2 (OFF)

    def test_cc_different_channel(self):
        """CC action on different channel."""
        action = Action(device="freak", type=ActionType.CC, cc=1, value=64)
        channel_map = {"freak": 5}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert msg_type == c.MSG_SW_MIDI_CC_TGGLE
        assert channel == 5
        assert data2 == 64  # value1 (ON)
        assert data3 == 0   # value2 (OFF)


class TestActionToMidiUnknownDevice:
    """Tests for unknown device handling."""

    def test_unknown_device_channel_zero(self):
        """Unknown device defaults to channel 0."""
        action = Action(device="unknown", type=ActionType.PRESET, value=1)
        channel_map = {"boss": 5}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert channel == 0
