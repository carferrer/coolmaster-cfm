"""Existing entries load without migration or newly required settings."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.coolmaster import (
    _remove_legacy_lock_buttons,
    async_remove_config_entry_device,
    async_setup_entry,
)


@pytest.mark.parametrize(
    "swing,wakeup,timeout", [(False, False, None), (True, True, 5)]
)
async def test_existing_entry_and_serial_entry(swing, wakeup, timeout):
    entry = SimpleNamespace(
        data={"host": "bridge", "port": 10200, "swing_support": swing},
        entry_id="test-entry",
    )
    if wakeup:
        entry.data["send_wakeup_prompt"] = True
    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    bridge = MagicMock(info=AsyncMock(return_value={"version": "test"}))
    coordinator = MagicMock(async_config_entry_first_refresh=AsyncMock())
    with (
        patch(
            "custom_components.coolmaster.CoolMasterNet", return_value=bridge
        ) as factory,
        patch(
            "custom_components.coolmaster.CoolmasterDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch("custom_components.coolmaster._remove_legacy_lock_buttons") as cleanup,
    ):
        assert await async_setup_entry(hass, entry)
    expected = {"send_initial_line_feed": wakeup}
    if timeout:
        expected.update(read_timeout=timeout, swing_support=True)
    factory.assert_called_once_with("bridge", 10200, **expected)
    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    assert entry.runtime_data is coordinator
    cleanup.assert_called_once_with(hass, entry)


def test_removes_only_legacy_buttons_from_this_entry():
    """Keep the filter button and switches, even if their IDs share a suffix."""
    entry = SimpleNamespace(entry_id="coolmaster-entry")
    registry = MagicMock()
    entities = [
        SimpleNamespace(
            entity_id=f"button.test_{key}",
            domain="button",
            platform="coolmaster",
            unique_id=f"L1.001-{key}",
        )
        for key in (
            "lock_on",
            "unlock_on",
            "lock_temp",
            "unlock_temp",
            "lock_mode",
            "unlock_mode",
        )
    ]
    entities += [
        SimpleNamespace(
            entity_id="button.test_reset_filter",
            domain="button",
            platform="coolmaster",
            unique_id="L1.001-reset_filter",
        ),
        SimpleNamespace(
            entity_id="switch.test_lock_on",
            domain="switch",
            platform="coolmaster",
            unique_id="L1.001-lock_on",
        ),
        SimpleNamespace(
            entity_id="button.other_lock_on",
            domain="button",
            platform="other",
            unique_id="L1.001-lock_on",
        ),
    ]
    with (
        patch("custom_components.coolmaster.er.async_get", return_value=registry),
        patch(
            "custom_components.coolmaster.er.async_entries_for_config_entry",
            return_value=entities,
        ) as entries_for_entry,
    ):
        _remove_legacy_lock_buttons(MagicMock(), entry)
    entries_for_entry.assert_called_once_with(registry, "coolmaster-entry")
    assert {call.args[0] for call in registry.async_remove.call_args_list} == {
        f"button.test_{key}"
        for key in (
            "lock_on",
            "unlock_on",
            "lock_temp",
            "unlock_temp",
            "lock_mode",
            "unlock_mode",
        )
    }


async def test_no_bridge_info_retries_setup():
    entry = SimpleNamespace(data={"host": "bridge", "port": 10102})
    bridge = MagicMock(info=AsyncMock(return_value={}))
    with patch("custom_components.coolmaster.CoolMasterNet", return_value=bridge):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(MagicMock(), entry)


async def test_device_removal_only_for_absent_units():
    entry = SimpleNamespace(runtime_data=SimpleNamespace(data={"L1.001": object()}))
    present = SimpleNamespace(identifiers={("coolmaster", "L1.001")})
    absent = SimpleNamespace(identifiers={("coolmaster", "L1.002")})
    assert not await async_remove_config_entry_device(MagicMock(), entry, present)
    assert await async_remove_config_entry_device(MagicMock(), entry, absent)
