# ABOUTME: Protocol constants for Nektar Pacer SysEx communication.
# ABOUTME: Based on pacer-editor/src/pacer/constants.js and sysex.js.

SYSEX_START = 0xF0
SYSEX_END = 0xF7
MANUFACTURER_ID = bytes([0x00, 0x01, 0x77])
DEVICE_ID = 0x7F

CMD_SET = 0x01
CMD_GET = 0x02

TARGET_PRESET = 0x01
TARGET_GLOBAL = 0x05

# Control IDs (Object byte dla control steps/mode/LED)
STOMPSWITCHES = {i: 0x0D + i for i in range(6)}  # SW1-SW6

# Special Object IDs
CONTROL_NAME = 0x01  # Object ID dla nazwy presetu

# Element IDs
CONTROL_MODE_ELEMENT = 0x60  # Element dla trybu kontrolki

# Message types (używane w control step data)
MSG_CTRL_OFF = 0x61       # Kontrolka wyłączona
MSG_SW_PRG_BANK = 0x45    # Program Change + Bank (PRESET)
MSG_SW_PRG_STEP = 0x46    # Program Step (PATTERN - start/end)
MSG_AD_MIDI_CC = 0x00     # Control Change (CC)

# LED colors
LED_OFF = 0x00
LED_GREEN = 0x0D
LED_RED = 0x03

# Preset mapping: "A1" -> 0x00, "F8" -> 0x2F
PRESET_INDICES = {
    f"{row}{col}": (ord(row) - ord('A')) * 8 + (col - 1)
    for row in "ABCDEF" for col in range(1, 9)
}
