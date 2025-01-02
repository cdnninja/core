"""Binary Sensor for VeSync."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from pyvesync.vesyncbasedevice import VeSyncBaseDevice

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import rgetattr
from .const import DOMAIN, VS_FANS
from .entity import VeSyncBaseEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class VeSyncBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A class that describes custom binary sensor entities."""

    is_on: Callable[[VeSyncBaseDevice], bool]


SENSOR_DESCRIPTIONS: tuple[VeSyncBinarySensorEntityDescription, ...] = (
    VeSyncBinarySensorEntityDescription(
        key="water_lacks",
        translation_key="water_lacks",
        is_on=lambda device: device.water_lacks,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    VeSyncBinarySensorEntityDescription(
        key="details.water_tank_lifted",
        translation_key="water_tank_lifted",
        is_on=lambda device: device.details["water_tank_lifted"],
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary_sensor platform."""
    entities: list[VeSyncBinarySensor] = []
    for device in hass.data[DOMAIN][VS_FANS]:
        for description in SENSOR_DESCRIPTIONS:
            if rgetattr(device, description.key) is not None:
                entities.append(VeSyncBinarySensor(device, description))  # noqa: PERF401
    async_add_entities(entities)


class VeSyncBinarySensor(BinarySensorEntity, VeSyncBaseEntity):
    """Vesync Connect binary sensor class."""

    def __init__(
        self,
        device: VeSyncBaseDevice,
        description: VeSyncBinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(device)
        self.entity_description: VeSyncBinarySensorEntityDescription = description
        self._attr_unique_id = f"{super().unique_id}-{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.entity_description.is_on is not None:
            return self.entity_description.is_on(self.device)
        return None
