"""Remote-controller locks with state read from CoolMasterNet."""

from dataclasses import dataclass
from typing import override

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CoolmasterConfigEntry, CoolmasterDataUpdateCoordinator
from .entity import CoolmasterEntity


@dataclass(frozen=True, kw_only=True)
class CoolmasterLockDescription(SwitchEntityDescription):
    """A lock flag reported by the bridge."""

    flag: str


LOCKS = (
    CoolmasterLockDescription(
        key="lock_on",
        translation_key="lock_on",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-outline",
        flag="o",
    ),
    CoolmasterLockDescription(
        key="lock_temp",
        translation_key="lock_temp",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-outline",
        flag="t",
    ),
    CoolmasterLockDescription(
        key="lock_mode",
        translation_key="lock_mode",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-outline",
        flag="m",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CoolmasterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create a switch for each lock type and unit."""
    coordinator = config_entry.runtime_data
    async_add_entities(
        CoolmasterLock(coordinator, unit_id, description)
        for unit_id in coordinator.data
        for description in LOCKS
    )


class CoolmasterLock(CoolmasterEntity, SwitchEntity):
    """Control a lock while showing only the bridge's reported state."""

    entity_description: CoolmasterLockDescription

    def __init__(
        self,
        coordinator: CoolmasterDataUpdateCoordinator,
        unit_id: str,
        description: CoolmasterLockDescription,
    ) -> None:
        self.entity_description = description
        super().__init__(coordinator, unit_id)

    @property
    @override
    def available(self) -> bool:
        """An unreported lock must not look unlocked."""
        return super().available and self.is_on is not None

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the actual lock state reported by the bridge."""
        return self._unit.lock_state(self.entity_description.flag)

    async def _set_lock(self, enabled: bool) -> None:
        try:
            unit = await self._unit._set_lock(self.entity_description.flag, enabled)
        except (OSError, ValueError) as error:
            raise HomeAssistantError(str(error)) from error
        self.coordinator.async_set_unit_data(unit)

    @override
    async def async_turn_on(self, **kwargs) -> None:
        """Enable the lock and read back the result."""
        await self._set_lock(True)

    @override
    async def async_turn_off(self, **kwargs) -> None:
        """Disable the lock and read back the result."""
        await self._set_lock(False)
