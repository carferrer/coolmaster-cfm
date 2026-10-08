"""Failures and command updates must preserve consistent entity state."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.coolmaster.coordinator import CoolmasterDataUpdateCoordinator


@pytest.fixture
def coordinator():
    return CoolmasterDataUpdateCoordinator(
        MagicMock(), MagicMock(), MagicMock(), {"version": "test"}
    )


@pytest.mark.parametrize(
    "failures",
    [
        [OSError("offline"), OSError("offline"), OSError("offline")],
        [{}, {}, {}],
        [{}, OSError("offline"), {}],
    ],
)
async def test_retries_are_bounded_with_no_final_sleep(coordinator, failures):
    coordinator._coolmaster.status = AsyncMock(side_effect=failures)
    with patch(
        "custom_components.coolmaster.coordinator.asyncio.sleep", new_callable=AsyncMock
    ) as sleep:
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    assert coordinator._coolmaster.status.await_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == [2, 4]


async def test_recovery_on_last_attempt(coordinator):
    recovered = {"L1.001": object()}
    coordinator._coolmaster.status = AsyncMock(side_effect=[OSError(), {}, recovered])
    with patch(
        "custom_components.coolmaster.coordinator.asyncio.sleep", new_callable=AsyncMock
    ):
        assert await coordinator._async_update_data() is recovered


def test_command_update_keeps_other_units_and_notifies_listeners(coordinator):
    other_unit = object()
    coordinator.data = {"L1.001": object(), "L1.002": other_unit}
    updated = MagicMock(unit_id="L1.001")
    # Do not schedule polling; this test only needs the real notification path.
    listener = MagicMock()
    coordinator._listeners[0] = (listener, None)
    with patch.object(coordinator, "_schedule_refresh"):
        coordinator.async_set_unit_data(updated)
    assert coordinator.data == {"L1.001": updated, "L1.002": other_unit}
    listener.assert_called_once()
