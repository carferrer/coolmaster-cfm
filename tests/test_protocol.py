"""Protocol regressions using a local TCP bridge, not HVAC hardware."""

import asyncio
import unittest
from unittest.mock import AsyncMock

from custom_components.coolmaster._vendor import (
    CoolMasterNet,
    CoolMasterNetCommandError,
    CoolMasterNetConnectionError,
)
from custom_components.coolmaster._vendor.coolmasternet import CoolMasterNetUnit

STATUS = "L1.001 ON 23.0C 24.0C Med Cool OK - 1"


class UnitTests(unittest.IsolatedAsyncioTestCase):
    def unit(self, raw=STATUS):
        bridge = CoolMasterNet("unused")
        bridge._make_request = AsyncMock(return_value="")
        return CoolMasterNetUnit(bridge, "L1.001", raw, "", "ls2")

    def test_demand_and_legacy_status(self):
        for flag, expected in [("0", False), ("1", True), ("2", True)]:
            with self.subTest(flag=flag):
                self.assertIs(self.unit(STATUS[:-1] + flag).demand, expected)
        legacy = self.unit("L1.001 ON 23,5C 24,0C Med Cool OK 1")
        self.assertIsNone(legacy.demand)
        self.assertTrue(legacy.clean_filter)
        self.assertEqual(legacy.thermostat, 23.5)
        self.assertEqual(legacy.temperature, 24.0)

    def test_malformed_status_is_connection_error(self):
        for status in ["", STATUS.replace("23.0C", "badC")]:
            with (
                self.subTest(status=status),
                self.assertRaises(CoolMasterNetConnectionError),
            ):
                self.unit(status)

    async def test_all_existing_lock_methods(self):
        for name, flag in [
            ("lockon", "+o"),
            ("unlockon", "-o"),
            ("locktemp", "+t"),
            ("unlocktemp", "-t"),
            ("lockmode", "+m"),
            ("unlockmode", "-m"),
        ]:
            with self.subTest(name=name):
                unit = self.unit()
                updated = self.unit(STATUS[:-1] + "0")
                unit.refresh = AsyncMock(return_value=updated)
                self.assertIs(await getattr(unit, name)(), updated)
                unit._bridge._make_request.assert_awaited_once_with(
                    f"lock L1.001 {flag}"
                )
                unit.refresh.assert_awaited_once()

    async def test_empty_status(self):
        bridge = CoolMasterNet("unused")
        bridge._make_request = AsyncMock(return_value="\r\n")
        self.assertEqual(await bridge.status(), {})

    async def test_fallback_cached_and_long_unit_id_preserved(self):
        bridge = CoolMasterNet("unused")
        raw = "L12.1234 ON 23.0C 24.0C Med Cool OK -"
        bridge._make_request = AsyncMock(
            side_effect=[CoolMasterNetCommandError(), raw, raw]
        )
        unit = (await bridge.status())["L12.1234"]
        self.assertIsNone(unit.demand)
        await unit.refresh()
        self.assertEqual(
            [c.args[0] for c in bridge._make_request.await_args_list],
            ["ls2", "stat2", "stat2 L12.1234"],
        )

    async def test_empty_single_unit_refresh(self):
        unit = self.unit()
        with self.assertRaises(CoolMasterNetConnectionError):
            await unit.refresh()

    async def test_rejected_lock_does_not_refresh(self):
        unit = self.unit()
        unit._bridge._make_request.side_effect = CoolMasterNetCommandError(
            "Unsupported"
        )
        unit.refresh = AsyncMock()
        with self.assertRaises(CoolMasterNetCommandError):
            await unit.lockon()
        unit.refresh.assert_not_awaited()

    async def test_temperature_rounding(self):
        unit = self.unit()
        unit.refresh = AsyncMock()
        await unit.set_thermostat(23.456)
        unit._bridge._make_request.assert_awaited_once_with("temp L1.001 23.5")


class TCPTests(unittest.IsolatedAsyncioTestCase):
    async def exchange(self, prompt=b">", wakeup=False, response=None):
        requests = []
        finished = asyncio.Event()

        async def handle(reader, writer):
            try:
                if wakeup:
                    requests.append(await reader.readline())
                writer.write(prompt)
                await writer.drain()
                requests.append(await reader.readline())
                writer.write(
                    response
                    if response is not None
                    else (STATUS + "\r\nOK\r\n>").encode()
                )
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
                finished.set()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            bridge = CoolMasterNet(
                "127.0.0.1", port, read_timeout=1, send_initial_line_feed=wakeup
            )
            try:
                result = await bridge._make_request("ls2")
            finally:
                await asyncio.wait_for(finished.wait(), 2)
        return result, requests

    async def test_network_and_both_serial_prompts(self):
        for prompt, wakeup in [(b">", False), (b"\r\n>", True), (b">>", True)]:
            with self.subTest(prompt=prompt):
                result, requests = await self.exchange(prompt, wakeup)
                self.assertEqual(result.strip(), STATUS)
                self.assertEqual(requests, [b"\n", b"ls2\n"] if wakeup else [b"ls2\n"])

    async def test_unknown_command(self):
        with self.assertRaises(CoolMasterNetCommandError):
            await self.exchange(response=b"Unknown command\r\n>")

    async def test_disconnected_response(self):
        with self.assertRaises(CoolMasterNetConnectionError):
            await self.exchange(response=b"partial")


if __name__ == "__main__":
    unittest.main()
