"""Configuration compatibility, duplicate prevention and reconfiguration."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import AbortFlow

from custom_components.coolmaster.config_flow import CoolmasterConfigFlow


@pytest.fixture
def flow():
    result = CoolmasterConfigFlow()
    result.hass = MagicMock()
    result.handler = "coolmaster"
    result.context = {"source": "user"}
    result._async_current_entries = MagicMock(return_value=[])
    return result


def user_data():
    return {
        "host": "bridge",
        "off": True,
        "heat": True,
        "cool": True,
        "dry": False,
        "heat_cool": False,
        "fan_only": True,
        "swing_support": False,
        "more_options": {"send_wakeup_prompt": True},
    }


async def test_new_config_and_wakeup_option(flow):
    bridge = MagicMock(status=AsyncMock(return_value={"L1.001": object()}))
    with patch(
        "custom_components.coolmaster.config_flow.CoolMasterNet", return_value=bridge
    ) as factory:
        result = await flow.async_step_user(user_data())
    factory.assert_called_once_with("bridge", 10102, send_initial_line_feed=True)
    assert result["type"] == "create_entry"
    assert result["data"]["supported_modes"] == ["off", "heat", "cool", "fan_only"]
    assert result["data"]["send_wakeup_prompt"] is True


@pytest.mark.parametrize(
    "response,error", [({}, "no_units"), (OSError("offline"), "cannot_connect")]
)
async def test_connection_errors_remain_in_form(flow, response, error):
    bridge = MagicMock(status=AsyncMock(side_effect=[response]))
    with patch(
        "custom_components.coolmaster.config_flow.CoolMasterNet", return_value=bridge
    ):
        result = await flow.async_step_user(user_data())
    assert result["errors"] == {"base": error}


async def test_duplicate_host_is_rejected_before_connection(flow):
    entry = SimpleNamespace(entry_id="other", data={"host": "bridge"}, options={})
    flow._async_current_entries.return_value = [entry]
    with patch("custom_components.coolmaster.config_flow.CoolMasterNet") as factory:
        with pytest.raises(AbortFlow) as raised:
            await flow.async_step_user(user_data())
    assert raised.value.reason == "already_configured"
    factory.assert_not_called()


async def test_reconfigure_legacy_entry_keeps_port_and_same_entry(flow):
    entry = SimpleNamespace(
        entry_id="existing",
        data={
            "host": "bridge",
            "port": 10200,
            "supported_modes": ["off", "cool"],
            "swing_support": True,
        },
        options={},
    )
    flow.context = {"source": "reconfigure", "entry_id": entry.entry_id}
    flow._async_current_entries.return_value = [entry]
    flow.hass.config_entries.async_get_known_entry.return_value = entry
    form = await flow.async_step_reconfigure()
    assert form["step_id"] == "reconfigure"
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    bridge = MagicMock(status=AsyncMock(return_value={"L1.001": object()}))
    with patch(
        "custom_components.coolmaster.config_flow.CoolMasterNet", return_value=bridge
    ) as factory:
        await flow.async_step_reconfigure(user_data())
    factory.assert_called_once_with("bridge", 10200, send_initial_line_feed=True)
    args, kwargs = flow.async_update_reload_and_abort.call_args
    assert args == (entry,)
    assert "port" not in kwargs["data_updates"]
    assert kwargs["data_updates"]["supported_modes"] == [
        "off",
        "heat",
        "cool",
        "fan_only",
    ]


async def test_reconfigure_cannot_take_another_entries_host(flow):
    original = SimpleNamespace(
        entry_id="existing", data={"host": "old", "port": 10102}, options={}
    )
    other = SimpleNamespace(entry_id="other", data={"host": "bridge"}, options={})
    flow.context = {"source": "reconfigure", "entry_id": "existing"}
    flow._async_current_entries.return_value = [original, other]
    flow.hass.config_entries.async_get_known_entry.return_value = original
    with pytest.raises(AbortFlow):
        await flow.async_step_reconfigure(user_data())
