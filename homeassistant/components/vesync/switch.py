"""Support for VeSync switches."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, Final

from pyvesync.vesyncbasedevice import VeSyncBaseDevice
from pyvesync.vesyncoutlet import VeSyncOutlet
from pyvesync.vesyncswitch import VeSyncSwitch

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import rgetattr
from .const import DOMAIN, VS_COORDINATOR, VS_DISCOVERY, VS_SWITCHES
from .coordinator import VeSyncDataCoordinator
from .entity import VeSyncBaseEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class VeSyncSwitchEntityDescription(SwitchEntityDescription):
    """A class that describes custom switch entities."""

    is_on: Callable[[VeSyncBaseDevice], bool]


SENSOR_DESCRIPTIONS: Final[tuple[VeSyncSwitchEntityDescription, ...]] = (
    VeSyncSwitchEntityDescription(
        key="device_status",
        translation_key="on",
        is_on=lambda device: device.device_status == "on",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch platform."""

    coordinator = hass.data[DOMAIN][VS_COORDINATOR]

    @callback
    def discover(devices):
        """Add new devices to platform."""
        _setup_entities(devices, async_add_entities, coordinator)

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, VS_DISCOVERY.format(VS_SWITCHES), discover)
    )

    _setup_entities(hass.data[DOMAIN][VS_SWITCHES], async_add_entities, coordinator)


@callback
def _setup_entities(
    devices: list[VeSyncBaseDevice],
    async_add_entities,
    coordinator: VeSyncDataCoordinator,
):
    """Check if device is online and add entity."""
    async_add_entities(
        (
            VeSyncSwitchEntity(dev, description, coordinator)
            for dev in devices
            for description in SENSOR_DESCRIPTIONS
            if rgetattr(dev, description.key) is not None
        ),
        update_before_add=True,
    )

class VeSyncBaseSwitch(VeSyncBaseEntity, SwitchEntity):
    """Base class for VeSync switch Device Representations."""

class VeSyncSwitchEntity(SwitchEntity, VeSyncBaseEntity):
    """VeSync sensor class."""

    def __init__(
        self,
        device: VeSyncBaseDevice,
        description: VeSyncSwitchEntityDescription,
        coordinator: VeSyncDataCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(device, coordinator)
        self.entity_description: VeSyncSwitchEntityDescription = description
        if isinstance(self.device, VeSyncOutlet):
            self._attr_device_class = SwitchDeviceClass.OUTLET
        if isinstance(self.device, VeSyncSwitch):
            self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_name = None

    @property
    def is_on(self) -> bool | None:
        """Return the entity value to represent the entity state."""
        if self.entity_description.is_on is not None:
            return self.entity_description.is_on(self.device)
        return None

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self.device.turn_off()

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self.device.turn_on()

    @property
    def is_on(self) -> bool:
        """Return True if device is on."""
        return self.device.device_status == "on"

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self.device.turn_off()


class VeSyncSwitchHA(VeSyncBaseSwitch, SwitchEntity):
    """Representation of a VeSync switch."""

    def __init__(
        self, plug: VeSyncBaseDevice, coordinator: VeSyncDataCoordinator
    ) -> None:
        """Initialize the VeSync switch device."""
        super().__init__(plug, coordinator)
        self.smartplug = plug


class VeSyncLightSwitch(VeSyncBaseSwitch, SwitchEntity):
    """Handle representation of VeSync Light Switch."""

    def __init__(
        self, switch: VeSyncBaseDevice, coordinator: VeSyncDataCoordinator
    ) -> None:
        """Initialize Light Switch device class."""
        super().__init__(switch, coordinator)
        self.switch = switch
