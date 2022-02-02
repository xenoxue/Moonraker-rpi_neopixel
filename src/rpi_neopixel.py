# RPI_NEOPIXEL neopixel support
#
# Copyright (C) 2021-2022 Richard Mitchell <richardjm+moonraker@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

# Component to control the rpi_neopixel neopixel home system from AirCookie
# Github at https://github.com/Aircoookie/RPI_NEOPIXEL
# Wiki at https://kno.rpi_neopixel.ge/

from __future__ import annotations
from enum import Enum
import logging
import json
import asyncio
import serial_asyncio
import board
import neopixel
from . import klippy_apis
from confighelper import ConfigHelper
APIComp = klippy_apis.KlippyAPI


class OnOff(str, Enum):
    on: str = "on"
    off: str = "off"

class Strip():
    _COLORSIZE: int = 4

    def __init__(self: Strip,
                 name: str,
                 cfg: ConfigHelper):
        self.server = cfg.get_server()
        self.request_mutex = asyncio.Lock()

        self.name = name

        self.initial_preset: int = cfg.getint("initial_preset", -1)
        self.initial_red: float = cfg.getfloat("initial_red", 0.5)
        self.initial_green: float = cfg.getfloat("initial_green", 0.5)
        self.initial_blue: float = cfg.getfloat("initial_blue", 0.5)
        self.initial_white: float = cfg.getfloat("initial_white", 0.5)
        self.chain_count: int = cfg.getint("chain_count", 1)
        ORDER = neopixel.RGB
        self.neopixel = neopixel.NeoPixel(board.D18, 60, pixel_order=ORDER)
        self.neopixel.fill((255,255,255))
        # Supports rgbw always
        self._chain_data = bytearray(
            self.chain_count * self._COLORSIZE)

        self.onoff = OnOff.off
        self.preset = self.initial_preset
        self.server.register_event_handler('server:klippy_ready', self._init)

    async def _init(self) -> None:
        # subscribe neopixel update function
            
        kapis: APIComp = self.server.lookup_component('klippy_apis')
        #sub: Dict[str, Optional[List[str]]] = {"neopixel case": None}
        try:
            await kapis.subscribe_objects(
                {f'neopixel {self.name}': None})
        except ServerError as e:
            logging.info(
                f"{e}\nUnable to subscribe to rpi_neopixel {self.name} object")
        else:
            logging.info(f"rpi_neopixel {self.name} Subscribed")
        self.server.register_event_handler("server:status_update", self._status_update)

    async def _status_update(self, data: Dict[str, Any]) -> None:
        name = f"neopixel {self.name}"
        if name not in data:
            return
        ps = data[name]
        if "color_data" in ps:
            cd = ps["color_data"][0]
            #logging.info(f"color_data {cd}")
            red = cd.get("R",None)
            green = cd.get("G",None)
            blue = cd.get("B",None)
            self._update_color_data(red, green, blue, 1, None)

    def get_strip_info(self: Strip) -> Dict[str, Any]:
        return {
            "strip": self.name,
            "status": self.onoff,
            "chain_count": self.chain_count,
            "preset": self.preset,
            "error": self.error_state
        }

    async def initialize(self: Strip) -> None:
        self.send_full_chain_data = True
        self.onoff = OnOff.on
        self.preset = self.initial_preset
        if self.initial_preset >= 0:
            self._update_color_data(self.initial_red,
                                    self.initial_green,
                                    self.initial_blue,
                                    self.initial_white,
                                    None)
            await self.rpi_neopixel_on(self.initial_preset)
        else:
            await self.set_rpi_neopixel(self.initial_red,
                                self.initial_green,
                                self.initial_blue,
                                self.initial_white,
                                None,
                                True)

    def _update_color_data(self: Strip,
                           red: float, green: float, blue: float, white: float,
                           index: Optional[int]) -> None:
        red = int(red * 255. + .5)
        blue = int(blue * 255. + .5)
        green = int(green * 255. + .5)
        white = int(white * 255. + .5)
        led_data = [red, green, blue, white]
        self.neopixel.fill((red,green,blue))
        if index is None:
            self._chain_data[:] = led_data * self.chain_count
        else:
            elem_size = len(led_data)
            self._chain_data[(index-1)*elem_size:index*elem_size] = led_data

    async def send_rpi_neopixel_command_impl(self: Strip,
                                     state: Dict[str, Any]) -> None:
        pass

    def close(self: Strip):
        pass

    async def _send_rpi_neopixel_command(self: Strip,
                                 state: Dict[str, Any]) -> None:
        try:
            await self.send_rpi_neopixel_command_impl(state)

            self.error_state = None
        except Exception as e:
            msg = f"RPI_NEOPIXEL: Error {e}"
            self.error_state = msg
            logging.exception(msg)
            raise self.server.error(msg)

    async def rpi_neopixel_on(self: Strip, preset: int) -> None:
        self.onoff = OnOff.on
        logging.debug(f"RPI_NEOPIXEL: {self.name} on PRESET={preset}")
        if preset < 0:
            # RPI_NEOPIXEL_ON STRIP=strip (no args) - reset to default
            await self.initialize()
        else:
            self.send_full_chain_data = True
            self.preset = preset
            await self._send_rpi_neopixel_command({"on": True, "ps": preset})

    async def rpi_neopixel_off(self: Strip) -> None:
        logging.debug(f"RPI_NEOPIXEL: {self.name} off")
        self.onoff = OnOff.off
        # Without this calling SET_RPI_NEOPIXEL for a single pixel after RPI_NEOPIXEL_OFF
        # would send just that pixel
        self.send_full_chain_data = True
        await self._send_rpi_neopixel_command({"on": False})

    def _rpi_neopixel_pixel(self: Strip, index: int) -> List[int]:
        led_color_data: List[int] = []
        for p in self._chain_data[(index-1)*self._COLORSIZE:
                                  (index)*self._COLORSIZE]:
            led_color_data.append(p)
        return led_color_data

    async def set_rpi_neopixel(self: Strip,
                       red: float, green: float, blue: float, white: float,
                       index: Optional[int], transmit: bool) -> None:
        logging.debug(
            f"RPI_NEOPIXEL: {self.name} R={red} G={green} B={blue} W={white} "
            f"INDEX={index} TRANSMIT={transmit}")
        self._update_color_data(red, green, blue, white, index)
        if transmit:

            # Base command for setting an led (for all active segments)
            # See https://kno.rpi_neopixel.ge/interfaces/json-api/
            state: Dict[str, Any] = {"on": True,
                                     "tt": 0,
                                     "bri": 255,
                                     "seg": {"bri": 255, "i": []}}
            if index is None:
                # All pixels same color only send range command of first color
                self.send_full_chain_data = False
                state["seg"]["i"] = [0, self.chain_count, self._rpi_neopixel_pixel(1)]
            elif self.send_full_chain_data:
                # Send a full set of color data (e.g. previous preset)
                self.send_full_chain_data = False
                cdata = []
                for i in range(self.chain_count):
                    cdata.append(self._rpi_neopixel_pixel(i+1))
                state["seg"]["i"] = cdata
            else:
                # Only one pixel has changed since last full data sent
                # so send just that one
                state["seg"]["i"] = [index-1, self._rpi_neopixel_pixel(index)]

            # Send rpi_neopixel control command
            await self._send_rpi_neopixel_command(state)

            if self.onoff == OnOff.off:
                # Without a repeated call individual led control doesn't
                # turn the led strip back on or doesn't set brightness
                # correctly from off
                # Confirmed as a bug:
                # https://discord.com/channels/473448917040758787/757254961640898622/934135556370202645
                self.onoff = OnOff.on
                await self._send_rpi_neopixel_command(state)
        else:
            # If not transmitting this time easiest just to send all data when
            # next transmitting
            self.send_full_chain_data = True

class RPI_NEOPIXEL:
    def __init__(self: RPI_NEOPIXEL, config: ConfigHelper) -> None:
        self.server = config.get_server()
        # root_logger = logging.getLogger()
        # root_logger.setLevel(logging.DEBUG)

        prefix_sections = config.get_prefix_sections("rpi_neopixel")
        logging.info(f"rpi_neopixel component loading strips: {prefix_sections}")
        for section in prefix_sections:
            cfg = config[section]
        self.strips = {}
        self.strips["case"] = Strip("case",cfg)

        # Register two remote methods for GCODE
        self.server.register_remote_method("set_rpi_neopixel_state", self.set_rpi_neopixel_state)
        self.server.register_remote_method("set_rpi_neopixel", self.set_rpi_neopixel)
        
        # As moonraker is about making things a web api, let's try it
        # Yes, this is largely a cut-n-paste from power.py
        self.server.register_endpoint(
            "/machine/rpi_neopixel/strips", ["GET"],
            self._handle_list_strips)
        self.server.register_endpoint(
            "/machine/rpi_neopixel/status", ["GET"],
            self._handle_batch_rpi_neopixel_request)
        self.server.register_endpoint(
            "/machine/rpi_neopixel/on", ["POST"],
            self._handle_batch_rpi_neopixel_request)
        self.server.register_endpoint(
            "/machine/rpi_neopixel/off", ["POST"],
            self._handle_batch_rpi_neopixel_request)
        self.server.register_endpoint(
            "/machine/rpi_neopixel/strip", ["GET", "POST"],
            self._handle_single_rpi_neopixel_request)

    async def component_init(self) -> None:
        try:
            #self.strips["case"].fill((0, 0, 0))
            return
        except Exception as e:
            logging.exception(e)

    async def rpi_neopixel_on(self: RPI_NEOPIXEL, strip: str, preset: int) -> None:
        if strip not in self.strips:
            logging.info(f"Unknown RPI_NEOPIXEL strip: {strip}")
            return
        await self.strips[strip].rpi_neopixel_on(preset)

    # Full control of rpi_neopixel
    # state: True, False, "on", "off"
    # preset: rpi_neopixel preset (int) to use (ignored if state False or "Off")
    async def set_rpi_neopixel_state(self: RPI_NEOPIXEL, strip: str, state: str,
                             preset: int = -1) -> None:
        status = None

        if isinstance(state, bool):
            status = OnOff.on if state else OnOff.off
        elif isinstance(state, str):
            status = state.lower()
            if status in ["true", "false"]:
                status = OnOff.on if status == "true" else OnOff.off

        if status is None and preset == -1:
            logging.info(
                f"Invalid state received but no preset passed: {state}")
            return

        if strip not in self.strips:
            logging.info(f"Unknown RPI_NEOPIXEL strip: {strip}")
            return

        if status == OnOff.off:
            # All other arguments are ignored
            await self.strips[strip].rpi_neopixel_off()
        else:
            await self.strips[strip].rpi_neopixel_on(preset)

    # Individual pixel control, for compatibility with SET_LED
    async def set_rpi_neopixel(self: RPI_NEOPIXEL,
                       strip: str,
                       red: float = 0.,
                       green: float = 0.,
                       blue: float = 0.,
                       white: float = 0.,
                       index: Optional[int] = None,
                       transmit: int = 1) -> None:
        #self.strips["case"].fill((red,green,blue))
        if strip not in self.strips:
            logging.info(f"Unknown RPI_NEOPIXEL strip: {strip}")
            return
        if isinstance(index, int) and index < 0:
            index = None
        await self.strips[strip].set_rpi_neopixel(red, green, blue, white,
                                          index,
                                          True if transmit == 1 else False)

    async def _handle_list_strips(self,
                                  web_request: WebRequest
                                  ) -> Dict[str, Any]:
        strips = {name: strip.get_strip_info()
                  for name, strip in self.strips.items()}
        output = {"strips": strips}
        return output

    async def _handle_single_rpi_neopixel_request(self: RPI_NEOPIXEL,
                                          web_request: WebRequest
                                          ) -> Dict[str, Any]:
        strip_name: str = web_request.get_str('strip')
        preset: int = web_request.get_int('preset', -1)

        req_action = web_request.get_action()
        if strip_name not in self.strips:
            raise self.server.error(f"No valid strip named {strip_name}")
        strip = self.strips[strip_name]
        if req_action == 'GET':
            return {strip_name: strip.get_strip_info()}
        elif req_action == "POST":
            action = web_request.get_str('action').lower()
            if action not in ["on", "off", "toggle"]:
                raise self.server.error(
                    f"Invalid requested action '{action}'")
            result = await self._process_request(strip, action, preset)
        return {strip_name: result}

    async def _handle_batch_rpi_neopixel_request(self: RPI_NEOPIXEL,
                                         web_request: WebRequest
                                         ) -> Dict[str, Any]:
        args = web_request.get_args()
        ep = web_request.get_endpoint()
        if not args:
            raise self.server.error("No arguments provided")
        requested_strips = {k: self.strips.get(k, None) for k in args}
        result = {}
        req = ep.split("/")[-1]
        for name, strip in requested_strips.items():
            if strip is not None:
                result[name] = await self._process_request(strip, req, -1)
            else:
                result[name] = {"error": "strip_not_found"}
        return result

    async def _process_request(self: RPI_NEOPIXEL,
                               strip: Strip,
                               req: str,
                               preset: int
                               ) -> Dict[str, Any]:
        strip_onoff = strip.onoff

        if req == "status":
            return strip.get_strip_info()
        if req == "toggle":
            req = "on" if strip_onoff == OnOff.off else "off"
        if req in ["on", "off"]:
            # Always do something, could be turning off colors, or changing
            # preset, easier not to have to worry
            if req == "on":
                strip_onoff = OnOff.on
                await strip.rpi_neopixel_on(preset)
            else:
                strip_onoff = OnOff.off
                await strip.rpi_neopixel_off()
            return strip.get_strip_info()

        raise self.server.error(f"Unsupported rpi_neopixel request: {req}")

    def close(self) -> None:
        for strip in self.strips.values():
            strip.close()

def load_component(config: ConfigHelper) -> RPI_NEOPIXEL:
    return RPI_NEOPIXEL(config)
