"""Buttons for filter maintenance and remote-controller locks."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from ._vendor.coolmasternet import CoolMasterNetUnit
from .coordinator import CoolmasterConfigEntry, CoolmasterDataUpdateCoordinator
from .entity import CoolmasterEntity


@dataclass(frozen=True, kw_only=True)
class CoolmasterButtonDescription(ButtonEntityDescription):
    """Describe a command returning an updated unit snapshot."""

    press: Callable[[CoolMasterNetUnit], Awaitable[CoolMasterNetUnit]]


BUTTONS = (
    CoolmasterButtonDescription(
        key="reset_filter",
        translation_key="reset_filter",
        entity_category=EntityCategory.CONFIG,
        press=CoolMasterNetUnit.reset_filter,
    ),
    CoolmasterButtonDescription(
        key="lock_on",
        translation_key="lock_on",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-outline",
        press=CoolMasterNetUnit.lockon,
    ),
    CoolmasterButtonDescription(
        key="unlock_on",
        translation_key="unlock_on",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-open-outline",
        press=CoolMasterNetUnit.unlockon,
    ),
    CoolmasterButtonDescription(
        key="lock_temp",
        translation_key="lock_temp",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-outline",
        press=CoolMasterNetUnit.locktemp,
    ),
    CoolmasterButtonDescription(
        key="unlock_temp",
        translation_key="unlock_temp",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-open-outline",
        press=CoolMasterNetUnit.unlocktemp,
    ),
    CoolmasterButtonDescription(
        key="lock_mode",
        translation_key="lock_mode",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-outline",
        press=CoolMasterNetUnit.lockmode,
    ),
    CoolmasterButtonDescription(
        key="unlock_mode",
        translation_key="unlock_mode",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-open-outline",
        press=CoolMasterNetUnit.unlockmode,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CoolmasterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons with the existing unique IDs."""
    coordinator = config_entry.runtime_data
    async_add_entities(
        CoolmasterButton(coordinator, unit_id, description)
        for unit_id in coordinator.data
        for description in BUTTONS
    )


class CoolmasterButton(CoolmasterEntity, ButtonEntity):
    """Execute a command and share its returned state with all entities."""

    entity_description: CoolmasterButtonDescription

    def __init__(
        self,
        coordinator: CoolmasterDataUpdateCoordinator,
        unit_id: str,
        description: CoolmasterButtonDescription,
    ) -> None:
        self.entity_description = description
        super().__init__(coordinator, unit_id)

    @override
    async def async_press(self) -> None:
        """Run the command without an additional whole-bridge refresh."""
        try:
            unit = await self.entity_description.press(self._unit)
        except (OSError, ValueError) as error:
            raise HomeAssistantError(str(error)) from error
        self.coordinator.async_set_unit_data(unit)
