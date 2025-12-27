# ABOUTME: SysEx message builder for Nektar Pacer.
# ABOUTME: Generates properly formatted SysEx frames with checksum.

from . import constants as c


def checksum(data: bytes) -> int:
    """Suma bajtów od Manufacturer ID do końca danych (bez F0/F7)."""
    return (128 - (sum(data) % 128)) % 128


class PacerSysExBuilder:
    """Buduje pojedyncze wiadomości SysEx."""

    def __init__(self, preset_index: int):
        self.preset_index = preset_index

    def _build_preset_name_frame(self, data: bytes) -> bytes:
        """Ramka SysEx dla preset name (z Element w headerze)."""
        header = bytes([
            c.DEVICE_ID,
            c.CMD_SET,
            c.TARGET_PRESET,
            self.preset_index,
            c.CONTROL_NAME,
            0x00  # Element = 0 dla preset name
        ])
        payload = c.MANUFACTURER_ID + header + data
        cs = checksum(payload)
        return bytes([c.SYSEX_START]) + payload + bytes([cs, c.SYSEX_END])

    def build_preset_name(self, name: str) -> bytes:
        """Ustaw nazwę presetu (dynamiczna długość, max 8 ASCII)."""
        ascii_name = name.encode('ascii', errors='replace')[:8]
        # Format: [długość] [bajty ASCII...]
        data = bytes([len(ascii_name)]) + ascii_name
        return self._build_preset_name_frame(data)

    def build_control_step(
        self,
        control_id: int,
        step_index: int,
        msg_type: int,
        channel: int,
        data1: int,
        data2: int = 0,
        data3: int = 0,
        active: bool = True
    ) -> bytes:
        """Konfiguruj krok kontrolki.

        Struktura: dla każdego parametru: [element_id, 0x01, wartość, 0x00]
        gdzie element_id = (step_index-1)*6 + offset
        Ostatni parametr (active) NIE ma paddingu 0x00.
        """
        base = (step_index - 1) * 6
        params = []

        # Każdy parametr: [element, object_type=0x01, value, padding=0x00]
        params.extend([base + 1, 0x01, channel, 0x00])      # Channel
        params.extend([base + 2, 0x01, msg_type, 0x00])     # Message type
        params.extend([base + 3, 0x01, data1, 0x00])        # Data 1
        params.extend([base + 4, 0x01, data2, 0x00])        # Data 2
        params.extend([base + 5, 0x01, data3, 0x00])        # Data 3
        params.extend([base + 6, 0x01, int(active)])        # Active (bez paddingu)

        header = bytes([
            c.DEVICE_ID,
            c.CMD_SET,
            c.TARGET_PRESET,
            self.preset_index,
            control_id
        ])
        payload = c.MANUFACTURER_ID + header + bytes(params)
        cs = checksum(payload)
        return bytes([c.SYSEX_START]) + payload + bytes([cs, c.SYSEX_END])

    def build_control_mode(self, control_id: int, mode: int = 0) -> bytes:
        """Ustaw tryb kontrolki.

        Args:
            control_id: ID kontrolki (np. STOMPSWITCHES[0] dla SW1)
            mode: Tryb pracy (0 = All steps in one shot, 1 = Sequence, 2 = External Step Select)
        """
        header = bytes([
            c.DEVICE_ID,
            c.CMD_SET,
            c.TARGET_PRESET,
            self.preset_index,
            control_id,
            c.CONTROL_MODE_ELEMENT,
            0x01,  # length = 1 byte
            mode
        ])
        payload = c.MANUFACTURER_ID + header
        cs = checksum(payload)
        return bytes([c.SYSEX_START]) + payload + bytes([cs, c.SYSEX_END])
