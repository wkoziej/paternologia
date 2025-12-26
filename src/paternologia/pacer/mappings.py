# ABOUTME: Mapping Paternologia models to MIDI parameters for Pacer.
# ABOUTME: Converts Action types to SysEx message parameters.

from ..models import Action, ActionType, Device
from . import constants as c


def build_device_channel_map(devices: list[Device]) -> dict[str, int]:
    """Buduj mapę device_id → MIDI channel z listy urządzeń.

    Używa Device.midi_channel z modelu.
    """
    channel_map = {}
    for device in devices:
        channel_map[device.id] = device.midi_channel
    return channel_map


def get_device_channel(device_id: str, channel_map: dict[str, int]) -> int:
    """Get MIDI channel for device, fallback to 0 if unknown."""
    return channel_map.get(device_id, 0)


def pattern_to_program(value: int | str | None) -> int:
    """Konwertuj pattern ID na Program Change number.

    M:S: A01-A16 (0-15), B01-B16 (16-31), ..., F01-F16 (80-95)
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Format "A01", "B02", etc.
        if len(value) >= 2 and value[0].isalpha():
            bank = ord(value[0].upper()) - ord('A')  # A=0, B=1, ..., F=5
            if bank < 0 or bank > 5:
                return 0  # Invalid bank (not A-F)
            try:
                pattern = int(value[1:]) - 1  # 01→0, 02→1, ..., 16→15
                if pattern < 0 or pattern > 15:
                    return 0  # Invalid pattern number
                return bank * 16 + pattern
            except ValueError:
                return 0
    return 0  # fallback


def action_to_midi(
    action: Action,
    device_channel_map: dict[str, int]
) -> tuple[int, int, int, int, int]:
    """Konwertuj Action na parametry MIDI.

    Args:
        action: Akcja do skonwertowania
        device_channel_map: Mapa device_id → MIDI channel

    Returns:
        (msg_type, channel, data1, data2, data3)

    Dla MSG_SW_PRG_BANK: data1=program, data2=bank LSB, data3=bank MSB
    Dla MSG_AD_MIDI_CC: data1=CC number, data2=value, data3=unused (0)
    """
    channel = get_device_channel(action.device, device_channel_map)

    if action.type == ActionType.PRESET:
        # Program Change + Bank
        # data1 = program number, data2 = bank LSB, data3 = bank MSB
        program = action.value if isinstance(action.value, int) else 0
        return (
            c.MSG_SW_PRG_BANK,
            channel,
            program,
            action.bank_lsb,
            action.bank_msb
        )

    elif action.type == ActionType.PATTERN:
        # Pattern na Model:Samples = Program Change (jak preset)
        # M:S używa PC 0-95 do wyboru pattern 1-96
        program = pattern_to_program(action.value)
        return (c.MSG_SW_PRG_BANK, channel, program, 0, 0)

    elif action.type == ActionType.CC:
        # Control Change
        # action.value jest wymagane (walidowane przez model)
        cc_value = action.value if isinstance(action.value, int) else 0
        return (c.MSG_AD_MIDI_CC, channel, action.cc or 0, cc_value, 0)

    else:
        raise ValueError(f"Nieobsługiwany typ akcji: {action.type}")
