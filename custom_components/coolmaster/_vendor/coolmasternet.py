import asyncio
import re

_MODES = ["auto", "cool", "dry", "fan", "heat"]

_SWING_CHAR_TO_NAME = {
    "a": "auto",
    "h": "horizontal",
    "3": "30",
    "4": "45",
    "6": "60",
    "v": "vertical",
    "x": "stop",
}

_SWING_NAME_TO_CHAR = {value: key for key, value in _SWING_CHAR_TO_NAME.items()}

SWING_MODES = list(_SWING_CHAR_TO_NAME.values())


class CoolMasterNetError(Exception):
    """Base class for errors raised by this library."""


class CoolMasterNetConnectionError(CoolMasterNetError, ConnectionError):
    """The bridge could not be reached, or did not answer as expected.

    Subclasses ConnectionError, and so OSError, so that callers already
    catching those keep working.
    """


class CoolMasterNetCommandError(CoolMasterNetError, ValueError):
    """The bridge rejected a command.

    Subclasses ValueError for backwards compatibility, which also keeps the
    ls2/stat2 fallback in _status working.
    """


class CoolMasterNet:
    """A connection to a coolmasternet bridge."""

    def __init__(
        self,
        host,
        port=10102,
        read_timeout=1,
        swing_support=False,
        send_initial_line_feed=False,
    ):
        """Initialize this CoolMasterNet instance to connect to a particular
        host at a particular port."""
        self._host = host
        self._port = port
        self._read_timeout = read_timeout
        self._swing_support = swing_support
        self._send_initial_line_feed = send_initial_line_feed
        self._status_cmd = None
        self._concurrent_reads = asyncio.Semaphore(3)

    async def _make_request(self, request):
        """Send a request to the CoolMasterNet and returns the response."""
        async with self._concurrent_reads:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), self._read_timeout
            )

            try:
                if self._send_initial_line_feed:
                    writer.write(b"\n")
                    await writer.drain()
                    # readuntil(tuple) requires Python 3.13. Accept both serial
                    # prompts while retaining compatibility with Python 3.12.
                    prompt = await asyncio.wait_for(
                        reader.readuntil(b">"), self._read_timeout
                    )
                    if prompt == b">":
                        prompt += await asyncio.wait_for(
                            reader.readexactly(1), self._read_timeout
                        )
                    if prompt not in (b"\r\n>", b">>"):
                        raise CoolMasterNetConnectionError(
                            "CoolMasterNet prompt not found"
                        )

                else:
                    prompt = await asyncio.wait_for(
                        reader.readuntil(b">"), self._read_timeout
                    )
                    if prompt != b">":
                        raise CoolMasterNetConnectionError(
                            "CoolMasterNet prompt not found"
                        )

                writer.write((request + "\n").encode("ascii"))
                await writer.drain()
                response = await asyncio.wait_for(
                    reader.readuntil(b"\n>"), self._read_timeout
                )

                data = response.decode("ascii")

                if data.endswith("\n>"):
                    data = data[:-1]

                if data.endswith("OK\r\n"):
                    data = data[:-4]

                if "Unknown command" in data:
                    cmd = request.split(" ", 1)[0]
                    raise CoolMasterNetCommandError(f"Command '{cmd}' is not supported")

                return data
            except (asyncio.IncompleteReadError, asyncio.LimitOverrunError) as error:
                raise CoolMasterNetConnectionError(
                    "Incomplete CoolMasterNet response"
                ) from error
            finally:
                writer.close()
                await writer.wait_closed()

    async def info(self):
        """Get the general info the this CoolMasterNet."""
        raw = await self._make_request("set")
        if not raw.strip():
            return {}
        lines = raw.strip().split("\r\n")
        key_values = [re.split(r"\s*:\s*", line, 1) for line in lines]
        if any(len(pair) != 2 for pair in key_values):
            raise CoolMasterNetConnectionError("Unexpected bridge information format")
        return dict(key_values)

    async def _status(self, status_cmd=None, unit_id=None):
        """Fetch the status of all units or a single one, falls back to legacy
        format if necessary"""

        if status_cmd is None:
            cmds = ["ls2", "stat2"]
        else:
            cmds = [status_cmd]

        for cmd in cmds:
            try:
                final_cmd = f"{cmd} {unit_id}" if unit_id is not None else cmd
                status_lines = (
                    (await self._make_request(final_cmd)).strip().splitlines()
                )
                break
            except ValueError:
                continue
        else:
            raise CoolMasterNetConnectionError("Failed to execute status commands")

        return cmd, status_lines

    async def status(self):
        """Return a list of CoolMasterNetUnit objects with current status."""

        self._status_cmd, status_lines = await self._status(self._status_cmd)

        return {
            key: unit
            for unit, key in await asyncio.gather(
                *(
                    CoolMasterNetUnit.create(
                        self, line.split()[0], line, self._status_cmd
                    )
                    for line in status_lines
                    if line.strip()
                )
            )
        }


class CoolMasterNetUnit:
    """An immutable snapshot of a unit."""

    def __init__(self, bridge, unit_id, raw, swing_raw, status_cmd="ls2", lock_raw=""):
        """Initialize a unit snapshot."""
        self._raw = raw
        self._status_cmd = status_cmd
        self._swing_raw = swing_raw
        self._lock_raw = lock_raw
        self._unit_id = unit_id
        self._bridge = bridge
        self._parse()

    @classmethod
    async def create(cls, bridge, unit_id, raw=None, status_cmd=None):
        if raw is None or status_cmd is None:
            status_cmd, status_lines = await bridge._status(status_cmd, unit_id)
            if not status_lines:
                raise CoolMasterNetConnectionError(f"Unit {unit_id} returned no status")
            raw = status_lines[0]

        async def read_locks():
            try:
                return (await bridge._make_request(f"lock {unit_id}")).strip()
            except CoolMasterNetCommandError:
                # Older bridges may not support lock queries. Do not invent a
                # state from the last command sent by Home Assistant.
                return ""

        swing_raw, lock_raw = await asyncio.gather(
            bridge._make_request(f"query {unit_id} s")
            if bridge._swing_support
            else asyncio.sleep(0, result=""),
            read_locks(),
        )
        return cls(
            bridge, unit_id, raw, swing_raw.strip(), status_cmd, lock_raw
        ), unit_id

    def _parse(self):
        fields = re.split(r"\s+", self._raw.strip())

        if len(fields) not in (8, 9):
            raise CoolMasterNetConnectionError(
                "Unexpected status line format: " + str(fields)
            )

        self._is_on = fields[1] == "ON"
        self._temperature_unit = "imperial" if fields[2][-1] == "F" else "celsius"
        try:
            self._thermostat = float(fields[2][:-1].replace(",", "."))
            self._temperature = float(fields[3][:-1].replace(",", "."))
        except ValueError as error:
            raise CoolMasterNetConnectionError(
                "Invalid temperature in status"
            ) from error
        self._fan_speed = fields[4].lower()
        self._mode = fields[5].lower()
        self._error_code = fields[6] if fields[6] != "OK" else None
        self._clean_filter = fields[7] in ("#", "1")
        # Only the 9-field form (ls/ls2) carries the demand flag as the last
        # field. The 8-field form (stat2) stops at the filter sign, so demand
        # is unknown there rather than assumed to be off.
        self._demand = fields[8] != "0" if len(fields) > 8 else None
        self._swing = _SWING_CHAR_TO_NAME.get(self._swing_raw)
        self._locks = self._parse_locks(self._lock_raw)

    @staticmethod
    def _parse_locks(raw):
        """Parse the documented lock query response, never guess missing flags."""
        flags = {"o": None, "m": None, "t": None}
        tokens = raw.split()
        if tokens == ["+"] or tokens == ["-"]:
            return dict.fromkeys(flags, tokens[0] == "+")
        if not tokens or any(
            not re.fullmatch(r"[+-][omtn]", token) for token in tokens
        ):
            return flags
        for token in tokens:
            if token[1] in flags:
                flags[token[1]] = token[0] == "+"
        return flags

    async def _make_unit_request(self, request):
        return await self._bridge._make_request(request.replace("UID", self._unit_id))

    async def refresh(self):
        """Refresh the data from CoolMasterNet and return it as a new instance."""
        return (
            await CoolMasterNetUnit.create(
                self._bridge, self._unit_id, None, self._status_cmd
            )
        )[0]

    @property
    def unit_id(self):
        """The unit id."""
        return self._unit_id

    @property
    def is_on(self):
        """Is the unit on."""
        return self._is_on

    @property
    def thermostat(self):
        """The target temperature."""
        return self._thermostat

    @property
    def temperature(self):
        """The current temperature."""
        return self._temperature

    @property
    def fan_speed(self):
        """The fan spped."""
        return self._fan_speed

    @property
    def mode(self):
        """The current mode (e.g. heat, cool)."""
        return self._mode

    @property
    def error_code(self):
        """Error code on error, otherwise None."""
        return self._error_code

    @property
    def clean_filter(self):
        """True when the air filter needs to be cleaned."""
        return self._clean_filter

    @property
    def demand(self):
        """True when the unit is actively calling for heating/cooling.

        A unit can be on while idle, for example in dry mode once the room is
        already below the set point. Returns None when the bridge's status
        format does not report demand.
        """
        return self._demand

    @property
    def swing(self):
        """The current swing mode (e.g. horizontal)."""
        return self._swing

    @property
    def temperature_unit(self):
        return self._temperature_unit

    def lock_state(self, flag):
        """Return a confirmed lock state, or None when the bridge did not report it."""
        return self._locks[flag]

    async def set_fan_speed(self, value):
        """Set the fan speed."""
        await self._make_unit_request(f"fspeed UID {value}")
        return await self.refresh()

    async def set_mode(self, value):
        """Set the mode."""
        if value not in _MODES:
            raise ValueError(
                f"Unrecognized mode {value}. Valid values: {' '.join(_MODES)}"
            )

        await self._make_unit_request(value + " UID")
        return await self.refresh()

    async def set_thermostat(self, value):
        """Set the target temperature."""
        rounded = round(value, 1)
        await self._make_unit_request(f"temp UID {rounded}")
        return await self.refresh()

    async def set_swing(self, value):
        """Set the swing mode."""
        if value not in SWING_MODES:
            raise ValueError(
                f"Unrecognized swing mode {value}. Valid values: {', '.join(SWING_MODES)}"
            )

        return_value = await self._make_unit_request(
            f"swing UID {_SWING_NAME_TO_CHAR[value]}"
        )
        if return_value.startswith("Unsupported Feature"):
            raise CoolMasterNetCommandError(
                f"Unit {self._unit_id} doesn't support swing mode {value}."
            )

        return await self.refresh()

    async def turn_on(self):
        """Turn a unit on."""
        await self._make_unit_request("on UID")
        return await self.refresh()

    async def turn_off(self):
        """Turn a unit off."""
        await self._make_unit_request("off UID")
        return await self.refresh()

    async def reset_filter(self):
        """Report that the air filter was cleaned and reset the timer."""
        await self._make_unit_request("filt UID")
        return await self.refresh()

    async def feed(self, value):
        """Provides ambient temperature hint to the unit."""
        rounded = round(value, 1)
        await self._make_unit_request(f"feed UID {rounded}")

    async def _set_lock(self, flag, enabled):
        """Set a remote-controller lock and return the refreshed unit."""
        sign = "+" if enabled else "-"
        await self._make_unit_request(f"lock UID {sign}{flag}")
        return await self.refresh()

    async def lockon(self):
        """Lock the remote controller's on/off control."""
        return await self._set_lock("o", True)

    async def unlockon(self):
        """Unlock the remote controller's on/off control."""
        return await self._set_lock("o", False)

    async def locktemp(self):
        """Lock the remote controller's temperature control."""
        return await self._set_lock("t", True)

    async def unlocktemp(self):
        """Unlock the remote controller's temperature control."""
        return await self._set_lock("t", False)

    async def lockmode(self):
        """Lock the remote controller's operating mode control."""
        return await self._set_lock("m", True)

    async def unlockmode(self):
        """Unlock the remote controller's operating mode control."""
        return await self._set_lock("m", False)
