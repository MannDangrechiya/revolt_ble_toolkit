"""GATT object model: Services, Characteristics, Descriptors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag


class CharacteristicProperty(IntFlag):
    """Characteristic Properties bitmask (Bluetooth Core Spec, Vol 3, Part G)."""

    BROADCAST = 0x01
    READ = 0x02
    WRITE_WITHOUT_RESPONSE = 0x04
    WRITE = 0x08
    NOTIFY = 0x10
    INDICATE = 0x20
    AUTHENTICATED_SIGNED_WRITES = 0x40
    EXTENDED_PROPERTIES = 0x80


@dataclass(frozen=True, slots=True)
class Descriptor:
    """A characteristic descriptor (e.g. Client Characteristic Configuration)."""

    handle: int
    uuid: str


@dataclass(frozen=True, slots=True)
class Characteristic:
    """A GATT characteristic: its declaration/value handles and descriptors."""

    declaration_handle: int
    value_handle: int
    uuid: str
    properties: CharacteristicProperty
    descriptors: tuple[Descriptor, ...] = ()


@dataclass(frozen=True, slots=True)
class Service:
    """A GATT service (a handle range) and the characteristics found in it."""

    connection_handle: int
    start_handle: int
    end_handle: int
    uuid: str
    characteristics: tuple[Characteristic, ...] = ()
