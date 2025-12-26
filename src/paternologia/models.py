# ABOUTME: Pydantic models for Paternologia - MIDI device configurations and songs.
# ABOUTME: Defines Device, Action, PacerButton, DeviceSettings, and Song schemas.

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class ActionType(str, Enum):
    """Types of MIDI actions that can be performed."""

    PRESET = "preset"
    PATTERN = "pattern"
    CC = "cc"


class Device(BaseModel):
    """MIDI device definition with supported action types."""

    id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Display name of the device")
    description: str = Field(default="", description="Device description")
    action_types: list[ActionType] = Field(
        default_factory=list, description="Supported action types"
    )
    midi_channel: int = Field(
        default=0,
        ge=0,
        le=15,
        description="MIDI channel (0-15) for this device"
    )


class DevicesConfig(BaseModel):
    """Configuration file structure for devices.yaml."""

    devices: list[Device] = Field(default_factory=list)


class Action(BaseModel):
    """Single MIDI action performed by a PACER button."""

    device: str = Field(..., description="Target device ID")
    type: ActionType = Field(..., description="Action type")
    value: int | str | None = Field(default=None, description="Action value (preset/pattern number)")
    cc: int | None = Field(default=None, description="MIDI CC number (for cc type)")
    label: str | None = Field(default=None, description="Optional display label")
    bank_lsb: int = Field(
        default=0,
        ge=0,
        le=127,
        description="Bank LSB (CC 32) for PRESET type"
    )
    bank_msb: int = Field(
        default=0,
        ge=0,
        le=127,
        description="Bank MSB (CC 0) for PRESET type"
    )

    @model_validator(mode='after')
    def validate_cc_value(self) -> 'Action':
        """Wymaga value dla ActionType.CC."""
        if self.type == ActionType.CC and self.value is None:
            raise ValueError("ActionType.CC wymaga pola 'value' (0-127)")
        if self.type == ActionType.CC:
            if not isinstance(self.value, int) or self.value < 0 or self.value > 127:
                raise ValueError(f"ActionType.CC value musi być 0-127, otrzymano: {self.value}")
        return self


class PacerButton(BaseModel):
    """PACER button configuration with up to 6 actions."""

    name: str = Field(..., description="Button display name")
    actions: Annotated[list[Action], Field(max_length=6)] = Field(
        default_factory=list, description="Actions to perform (max 6)"
    )


class SongMetadata(BaseModel):
    """Song metadata information."""

    id: str = Field(..., description="Unique song identifier (filename without extension)")
    name: str = Field(..., description="Display name of the song")
    author: str = Field(default="", description="Song author")
    created: date = Field(default_factory=date.today, description="Creation date")
    notes: str = Field(default="", description="Additional notes")


class Song(BaseModel):
    """Complete song configuration with PACER buttons."""

    song: SongMetadata = Field(..., description="Song metadata")
    pacer: Annotated[list[PacerButton], Field(max_length=6)] = Field(
        default_factory=list, description="PACER button configurations (max 6)"
    )
