"""Button platform for CoolMasterNet integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CoolmasterConfigEntry
from .entity import CoolmasterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CoolmasterConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the CoolMasterNet button platform."""
    coordinator = config_entry.runtime_data
    async_add_entities(
        CoolmasterResetFilter(coordinator, unit_id) for unit_id in coordinator.data
    )
    async_add_entities(
        Coolmasterlockon(coordinator, unit_id) for unit_id in coordinator.data
    )
    async_add_entities(
        Coolmasterunlockon(coordinator, unit_id) for unit_id in coordinator.data
    )
    async_add_entities(
        Coolmasterlocktemp(coordinator, unit_id) for unit_id in coordinator.data
    )
    async_add_entities(
        Coolmasterunlocktemp(coordinator, unit_id) for unit_id in coordinator.data
    )
    async_add_entities(
        Coolmasterlockmode(coordinator, unit_id) for unit_id in coordinator.data
    )
    async_add_entities(
        Coolmasterunlockmode(coordinator, unit_id) for unit_id in coordinator.data
    )


class CoolmasterResetFilter(CoolmasterEntity, ButtonEntity):
    """Reset the clean filter timer (once filter was cleaned)."""

    entity_description = ButtonEntityDescription(
        key="reset_filter",
        translation_key="reset_filter",
        entity_category=EntityCategory.CONFIG,
    )

    async def async_press(self) -> None:
        """Press the button."""
        await self._unit.reset_filter()
        await self.coordinator.async_refresh()
        

class Coolmasterlockon(CoolmasterEntity, ButtonEntity):
    """Reset the clean filter timer (once filter was cleaned)."""

    entity_description = ButtonEntityDescription(
        key="lock_on",
        translation_key="lock_on",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-outline",
		name="Bloqueo on/off activar",
    )

    async def async_press(self) -> None:
        """Press the button."""
        await self._unit.lockon()
        await self.coordinator.async_refresh()

class Coolmasterunlockon(CoolmasterEntity, ButtonEntity):
    """Reset the clean filter timer (once filter was cleaned)."""

    entity_description = ButtonEntityDescription(
        key="unlock_on",
        translation_key="unlock_on",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-open-outline",
		name="Bloqueo on/off desactivar",
    )

    async def async_press(self) -> None:
        """Press the button."""
        await self._unit.unlockon()
        await self.coordinator.async_refresh()

class Coolmasterlocktemp(CoolmasterEntity, ButtonEntity):
    """Reset the clean filter timer (once filter was cleaned)."""

    entity_description = ButtonEntityDescription(
        key="lock_temp",
        translation_key="lock_temp",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-outline",
		name="Bloqueo temp. activar",
    )

    async def async_press(self) -> None:
        """Press the button."""
        await self._unit.locktemp()
        await self.coordinator.async_refresh()

class Coolmasterunlocktemp(CoolmasterEntity, ButtonEntity):
    """Reset the clean filter timer (once filter was cleaned)."""

    entity_description = ButtonEntityDescription(
        key="unlock_temp",
        translation_key="unlock_temp",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-open-outline",
		name="Bloqueo temp. desactivar",
    )

    async def async_press(self) -> None:
        """Press the button."""
        await self._unit.unlocktemp()
        await self.coordinator.async_refresh()

class Coolmasterlockmode(CoolmasterEntity, ButtonEntity):
    """Reset the clean filter timer (once filter was cleaned)."""

    entity_description = ButtonEntityDescription(
        key="lock_mode",
        translation_key="lock_mode",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-outline",
		name="Bloqueo modo activar",
    )

    async def async_press(self) -> None:
        """Press the button."""
        await self._unit.lockmode()
        await self.coordinator.async_refresh()

class Coolmasterunlockmode(CoolmasterEntity, ButtonEntity):
    """Reset the clean filter timer (once filter was cleaned)."""

    entity_description = ButtonEntityDescription(
        key="unlock_mode",
        translation_key="unlock_mode",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:shield-lock-open-outline",
		name="Bloqueo modo desactivar",
    )

    async def async_press(self) -> None:
        """Press the button."""
        await self._unit.unlockmode()
        await self.coordinator.async_refresh()


