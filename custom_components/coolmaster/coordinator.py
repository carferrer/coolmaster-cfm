"""DataUpdateCoordinator for coolmaster integration."""

import asyncio
import logging
from typing import override

from homeassistant.components.climate import SCAN_INTERVAL
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ._vendor import CoolMasterNet
from ._vendor.coolmasternet import CoolMasterNetUnit
from .const import BACKOFF_BASE_DELAY, DOMAIN, MAX_RETRIES

_LOGGER = logging.getLogger(__name__)


type CoolmasterConfigEntry = ConfigEntry[CoolmasterDataUpdateCoordinator]


class CoolmasterDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, CoolMasterNetUnit]]
):
    """Class to manage fetching Coolmaster data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CoolmasterConfigEntry,
        coolmaster: CoolMasterNet,
        info: dict[str, str],
    ) -> None:
        """Initialize global Coolmaster data updater."""
        self._coolmaster = coolmaster
        self.info = info

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    @override
    async def _async_update_data(self) -> dict[str, CoolMasterNetUnit]:
        """Fetch data from Coolmaster."""
        retries_left = MAX_RETRIES
        status: dict[str, CoolMasterNetUnit] = {}
        while retries_left > 0 and not status:
            retries_left -= 1
            try:
                status = await self._coolmaster.status()
            except OSError as error:
                if retries_left == 0:
                    raise UpdateFailed(
                        "Error communicating with Coolmaster"
                        f" (aborting after {MAX_RETRIES}"
                        f" retries): {error}"
                    ) from error
                _LOGGER.debug(
                    "Error communicating with coolmaster (%d retries left): %s",
                    retries_left,
                    str(error),
                )
            else:
                if status:
                    return status

                _LOGGER.debug(
                    "Error communicating with coolmaster:"
                    " empty status received (%d retries left)",
                    retries_left,
                )

            if retries_left:
                backoff = BACKOFF_BASE_DELAY ** (MAX_RETRIES - retries_left)
                await asyncio.sleep(backoff)

        raise UpdateFailed(
            "Error communicating with Coolmaster"
            f" (aborting after {MAX_RETRIES} retries):"
            " empty status received"
        )

    @callback
    def async_set_unit_data(self, unit: CoolMasterNetUnit) -> None:
        """Publish the command result without polling unrelated units."""
        self.async_set_updated_data({**self.data, unit.unit_id: unit})
