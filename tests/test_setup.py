"""Existing entries load without migration or newly required settings."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.coolmaster import (
    async_remove_config_entry_device,
    async_setup_entry,
)


@pytest.mark.parametrize(
    "swing,wakeup,timeout", [(False, False, None), (True, True, 5)]
)
async def test_existing_entry_and_serial_entry(swing, wakeup, timeout):
    entry = SimpleNamespace(
        data={"host": "bridge", "port": 10200, "swing_support": swing}
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
    ):
        assert await async_setup_entry(hass, entry)
    expected = {"send_initial_line_feed": wakeup}
    if timeout:
        expected.update(read_timeout=timeout, swing_support=True)
    factory.assert_called_once_with("bridge", 10200, **expected)
    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    assert entry.runtime_data is coordinator


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
