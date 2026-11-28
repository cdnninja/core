"""Class to manage VeSync data updates."""

from datetime import timedelta
import logging
import time
from typing import override

from pyvesync import VeSync
from pyvesync.utils.errors import VeSyncError, VeSyncLoginError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_ENERGY,
    UPDATE_INTERVAL_FIRMWARE,
)

_LOGGER = logging.getLogger(__name__)

type VesyncConfigEntry = ConfigEntry[VeSyncDataCoordinator]


class VeSyncDataCoordinator(DataUpdateCoordinator[None]):
    """Class representing data coordinator for VeSync devices."""

    config_entry: VesyncConfigEntry
    update_time: float | None = None

    def __init__(
        self, hass: HomeAssistant, config_entry: VesyncConfigEntry, manager: VeSync
    ) -> None:
        """Initialize."""
        self.manager = manager
        # Firmware is checked during config entry setup
        self.firmware_update_time = time.time()

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="VeSyncDataCoordinator",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    def should_update_energy(self) -> bool:
        """Test if specified update interval has been exceeded."""
        if self.update_time is None:
            return True

        return time.time() - self.update_time >= UPDATE_INTERVAL_ENERGY

    def should_check_firmware(self) -> bool:
        """Test if the firmware check interval has been exceeded."""
        return time.time() - self.firmware_update_time >= UPDATE_INTERVAL_FIRMWARE

    @override
    async def _async_update_data(self) -> None:
        """Fetch data from API endpoint."""
        try:
            await self.manager.update_all_devices()

            if self.should_update_energy():
                self.update_time = time.time()
                for outlet in self.manager.devices.outlets:
                    await outlet.update_energy()

            if self.should_check_firmware():
                await self.manager.check_firmware()
                self.firmware_update_time = time.time()
        except VeSyncLoginError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except VeSyncError as err:
            raise UpdateFailed(f"The service is unavailable: {err}") from err
