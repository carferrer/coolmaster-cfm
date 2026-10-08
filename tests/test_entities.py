"""Test custom entities against real Home Assistant entity classes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.exceptions import HomeAssistantError

from custom_components.coolmaster._vendor import (
    CoolMasterNet,
    CoolMasterNetCommandError,
)
from custom_components.coolmaster._vendor.coolmasternet import CoolMasterNetUnit
from custom_components.coolmaster.binary_sensor import (
    CoolmasterCleanFilter,
    CoolmasterDemand,
)
from custom_components.coolmaster.button import BUTTONS, CoolmasterButton
from custom_components.coolmaster.climate import CoolmasterClimate
from custom_components.coolmaster.entity import CoolmasterEntity
from custom_components.coolmaster.sensor import CoolmasterCleanFilter as ErrorSensor


def make_unit(raw="L1.001 ON 23.0C 24.0C Med Cool OK - 1"):
    bridge = CoolMasterNet("unused")
    bridge._make_request = AsyncMock(return_value="")
    return CoolMasterNetUnit(bridge, "L1.001", raw, "", "ls2")


@pytest.fixture
def coordinator():
    return SimpleNamespace(
        data={"L1.001": make_unit()},
        info={"version": "test"},
        last_update_success=True,
        config_entry=None,
        async_set_unit_data=MagicMock(),
        async_refresh=AsyncMock(),
    )


@pytest.mark.parametrize(
    "key,command",
    [
        ("reset_filter", "filt L1.001"),
        ("lock_on", "lock L1.001 +o"),
        ("unlock_on", "lock L1.001 -o"),
        ("lock_temp", "lock L1.001 +t"),
        ("unlock_temp", "lock L1.001 -t"),
        ("lock_mode", "lock L1.001 +m"),
        ("unlock_mode", "lock L1.001 -m"),
    ],
)
async def test_buttons_preserve_ids_and_publish_single_refresh(
    coordinator, key, command
):
    description = next(d for d in BUTTONS if d.key == key)
    unit = coordinator.data["L1.001"]
    updated = make_unit()
    unit.refresh = AsyncMock(return_value=updated)
    entity = CoolmasterButton(coordinator, "L1.001", description)
    assert entity.unique_id == f"L1.001-{key}"
    await entity.async_press()
    unit._bridge._make_request.assert_awaited_once_with(command)
    unit.refresh.assert_awaited_once()
    coordinator.async_set_unit_data.assert_called_once_with(updated)
    coordinator.async_refresh.assert_not_awaited()


async def test_button_error_is_actionable(coordinator):
    unit = coordinator.data["L1.001"]
    unit._bridge._make_request.side_effect = CoolMasterNetCommandError(
        "unsupported lock"
    )
    entity = CoolmasterButton(coordinator, "L1.001", BUTTONS[1])
    with pytest.raises(HomeAssistantError, match="unsupported lock"):
        await entity.async_press()
    coordinator.async_set_unit_data.assert_not_called()


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("L1.001 ON 23.0C 24.0C Med Cool OK - 1", True),
        ("L1.001 ON 23.0C 24.0C Med Cool OK - 0", False),
        ("L1.001 ON 23.0C 24.0C Med Cool OK -", None),
    ],
)
def test_demand_uses_public_property_and_can_be_unknown(coordinator, raw, expected):
    coordinator.data["L1.001"] = make_unit(raw)
    entity = CoolmasterDemand(coordinator, "L1.001")
    assert entity.unique_id == "L1.001-demand"
    assert entity.is_on is expected


def test_existing_entity_and_device_identifiers(coordinator):
    climate = CoolmasterClimate(coordinator, "L1.001", [HVACMode.OFF, HVACMode.COOL])
    assert climate.unique_id == "L1.001"
    assert climate.device_info["identifiers"] == {("coolmaster", "L1.001")}
    assert (
        CoolmasterCleanFilter(coordinator, "L1.001").unique_id == "L1.001-clean_filter"
    )
    assert ErrorSensor(coordinator, "L1.001").unique_id == "L1.001-error_code"


async def test_medium_fan_mode_maps_to_wire_protocol(coordinator):
    entity = CoolmasterClimate(coordinator, "L1.001", [HVACMode.COOL])
    entity.async_write_ha_state = MagicMock()
    unit = coordinator.data["L1.001"]
    unit.refresh = AsyncMock(return_value=unit)
    assert entity.fan_mode == "med"
    await entity.async_handle_set_fan_mode_service("med")
    unit._bridge._make_request.assert_awaited_once_with("fspeed L1.001 med")


def test_disappearing_unit_becomes_unavailable_and_recovers(coordinator):
    entity = CoolmasterEntity(coordinator, "L1.001")
    entity.async_write_ha_state = MagicMock()
    assert entity.available
    coordinator.data = {}
    entity._handle_coordinator_update()
    assert not entity.available
    new_unit = make_unit()
    coordinator.data = {"L1.001": new_unit}
    entity._handle_coordinator_update()
    assert entity.available
    assert entity._unit is new_unit
