# WLED neopixel support
#
# Copyright (C) 2021-2022 Richard Mitchell <richardjm+moonraker@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

# Component to control the wled neopixel home system from AirCookie
# Github at https://github.com/Aircoookie/WLED
# Wiki at https://kno.wled.ge/

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
    _COLORSIZE: int = 3

    def __init__(self: Strip,
                 name: str,
                 cfg: ConfigHelper):
        self.server = cfg.get_server()

        self.name = name

        self.initial_preset: int = cfg.getint("initial_preset", -1)
        self.initial_red: float = cfg.getfloat("initial_red", 0.5)
        self.initial_green: float = cfg.getfloat("initial_green", 0.5)
        self.initial_blue: float = cfg.getfloat("initial_blue", 0.5)
        self.initial_white: float = cfg.getfloat("initial_white", 0.5)
        self.chain_count: int = cfg.getint("chain_count", 1)
        self.gpio: int = cfg.getint("gpio", 18)
        self.order: str = cfg.get("order", "RGB")
        self.brightness: float = cfg.getfloat("brightness", 1)
        self.auto_write: bool = cfg.getboolean("auto_write", True)
        self.pixel_pin = board.D18
        if self.gpio == 10:
            self.pixel_pin = board.D10
        elif self.gpio == 12:
            self.pixel_pin = board.D12
        elif self.gpio == 21:
            self.pixel_pin = board.D21

        self.pixel_order = neopixel.RGB
        if self.order == "GRB":
            self.pixel_order = neopixel.GRB
        elif self.order == "RGBW":
            self.pixel_order = neopixel.RGBW
            self._COLORSIZE = 4
        elif self.order == "GRBW":
            self.pixel_order = neopixel.GRBW
            self._COLORSIZE = 4
        

        self.neopixel = neopixel.NeoPixel(self.pixel_pin, self.chain_count, brightness=self.brightness, auto_write=self.auto_write, pixel_order=self.pixel_order)
        
        self._chain_data = bytearray(
            self.chain_count * self._COLORSIZE)

        self.onoff = OnOff.off
        self.preset = self.initial_preset
        self.server.register_event_handler('server:klippy_ready', self._init)

    async def _init(self) -> None:
        # subscribe neopixel update function
        kapis: APIComp = self.server.lookup_component('klippy_apis')
        try:
            await kapis.subscribe_objects(
                {f'neopixel {self.name}': None})
        except ServerError as e:
            logging.info(
                f"{e}\nUnable to subscribe to rpi_neopixel {self.name} object")
        else:
            logging.info(f"rpi_neopixel {self.name} Subscribed")
        
        # register status_update event
        self.server.register_event_handler("server:status_update", self._status_update)

    # auto update color
    async def _status_update(self, data: Dict[str, Any]) -> None:
        name = f"neopixel {self.name}"
        if name not in data:
            return
        #logging.info(f"status_update {data}")
        ps = data[name]
        if "color_data" in ps:
            index = 0
            for chain in ps["color_data"]:
                red = chain.get("R",0)
                green = chain.get("G",0)
                blue = chain.get("B",0)
                white = chain.get("W",0)
                self._update_color_data(red, green, blue, white, index)
                index+=1

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
        led_data = (red, green, blue)

        if self.order == "GRB":
            led_data = (green, red, blue)
        elif self.order == "RGBW":
            led_data = (red, green, blue, white)
        elif self.order == "GRBW":
            led_data = (green, red, blue, white)

        if index == 0:
            index = None
        
        if index is None:
            self.neopixel.fill(led_data)
            #self._chain_data[:] = led_data * self.chain_count
        else:
            index = int(index)
            self.neopixel[index] = led_data
            #elem_size = len(led_data)
            #self._chain_data[(index-1)*elem_size:index*elem_size] = led_data

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
            self._update_color_data(self.initial_red,
                                    self.initial_green,
                                    self.initial_blue,
                                    self.initial_white,
                                    None)
            #await self._send_rpi_neopixel_command({"on": True, "ps": preset})

    async def rpi_neopixel_off(self: Strip) -> None:
        logging.debug(f"RPI_NEOPIXEL: {self.name} off")
        self.onoff = OnOff.off
        # Without this calling SET_RPI_NEOPIXEL for a single pixel after RPI_NEOPIXEL_OFF
        # would send just that pixel
        self.send_full_chain_data = True
        self._update_color_data(0,0,0,0,None)
        #await self._send_rpi_neopixel_command({"on": False})

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
            return
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
        self.strips = {}
        for section in prefix_sections:
            cfg = config[section]

            try:
                name_parts = cfg.get_name().split(maxsplit=1)
                if len(name_parts) != 2:
                    raise cfg.error(
                        f"Invalid Section Name: {cfg.get_name()}")
                name: str = name_parts[1]

                logging.info(f"rpi_neopixel strip: {name}")
                cfg.get("color_order", "", deprecate=True)

                self.strips[name] = Strip(name,cfg)

            except Exception as e:
                # Ensures errors such as "Color not supported" are visible
                msg = f"Failed to initialise strip [{cfg.get_name()}]\n{e}"
                self.server.add_warning(msg)
                continue

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
        if strip not in self.strips:
            logging.info(f"Unknown RPI_NEOPIXEL strip: {strip}")
            return
        
        if isinstance(index, int) and index <= 0:
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
