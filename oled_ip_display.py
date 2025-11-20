#!/usr/bin/env python3

"""Show hostname/IP on SSD1312 (luma.oled) or SH1107 (displayio) panels."""

from __future__ import annotations



import os

import socket

import subprocess

import time

from datetime import datetime



try:

    from luma.core.interface.serial import i2c as luma_i2c

    from luma.core.render import canvas

    from luma.oled.device import ssd1306 as luma_ssd1306

except ImportError:  # pragma: no cover

    luma_i2c = None  # type: ignore

    luma_ssd1306 = None  # type: ignore



try:

    import board

    import displayio

    import terminalio

    from adafruit_display_text import bitmap_label, label

    import adafruit_displayio_sh1107

    from i2cdisplaybus import I2CDisplayBus

except ImportError:  # pragma: no cover

    board = None  # type: ignore

    displayio = None  # type: ignore

    terminalio = None  # type: ignore

    label = None  # type: ignore

    adafruit_displayio_sh1107 = None  # type: ignore

    I2CDisplayBus = None  # type: ignore





def env_int(name: str, default: str) -> int:

    value = os.getenv(name, default)

    if value.lower().startswith("0x"):

        return int(value, 16)

    return int(value)





OLED_DRIVER = os.getenv("OLED_DRIVER", "ssd1312").lower()

OLED_WIDTH = env_int("OLED_WIDTH", "128")

OLED_HEIGHT = env_int("OLED_HEIGHT", "64")

OLED_ROTATE = env_int("OLED_ROTATE", "0") % 4

OLED_I2C_ADDR = env_int("OLED_I2C_ADDR", "0x3C")

REFRESH_SECONDS = env_int("OLED_REFRESH_SECS", "5")





def get_ip_address() -> str:

    try:

        result = subprocess.check_output(["hostname", "-I"], timeout=2)

        for part in result.decode().split():

            candidate = part.strip()

            if candidate and not candidate.startswith("127."):

                return candidate

    except Exception:

        pass

    try:

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.connect(("8.8.8.8", 80))

        ip_addr = sock.getsockname()[0]

        sock.close()

        return ip_addr

    except Exception:

        return "?"





class SSD1312Display:

    def __init__(self) -> None:

        if luma_i2c is None or luma_ssd1306 is None:

            raise RuntimeError("luma.oled is not installed")

        width = max(OLED_WIDTH, OLED_HEIGHT)

        height = min(OLED_WIDTH, OLED_HEIGHT)

        serial = luma_i2c(port=1, address=OLED_I2C_ADDR)

        self.device = luma_ssd1306(serial, width=width, height=height, rotate=OLED_ROTATE, mode="1")

        self.device.contrast(0x7F)



    def update(self, hostname: str, ip_addr: str, timestamp: str) -> None:

        with canvas(self.device) as draw:

            draw.text((0, 0), "PCM5102A Decoder", fill="white")

            draw.text((0, 14), f"Host: {hostname}", fill="white")

            draw.text((0, 28), f"IP: {ip_addr}", fill="white")

            draw.text((0, 44), f"Time {timestamp}", fill="white")



    def cleanup(self) -> None:

        self.device.hide()





class SH1107Display:

    def __init__(self) -> None:

        if (

            board is None

            or displayio is None

            or terminalio is None

            or adafruit_displayio_sh1107 is None

            or label is None

            or I2CDisplayBus is None

        ):

            raise RuntimeError(

                "displayio SH1107 libs missing. Install adafruit-circuitpython-displayio-sh1107 "

                "adafruit-circuitpython-display-text and adafruit-blinka-displayio."

            )

        displayio.release_displays()

        i2c = board.I2C()

        display_bus = I2CDisplayBus(i2c, device_address=OLED_I2C_ADDR)

        rotation_deg = OLED_ROTATE * 90

        controller_width = OLED_WIDTH

        controller_height = OLED_HEIGHT

        self.display = adafruit_displayio_sh1107.SH1107(

            display_bus,

            width=controller_width,

            height=controller_height,

            rotation=rotation_deg,

        )

        self.group = displayio.Group()

        width = getattr(self.display, "width", OLED_WIDTH)

        self.header = bitmap_label.Label(terminalio.FONT, text="PCM5102A", color=0xFFFFFF)

        self.header.anchor_point = (0.5, 0.0)

        self.header.anchored_position = (width // 2, 2)

        self.ip_big = bitmap_label.Label(terminalio.FONT, text="", color=0xFFFFFF)

        self.ip_big.anchor_point = (0.5, 0.0)

        self.ip_big.anchored_position = (width // 2, 20)

        self.status = bitmap_label.Label(terminalio.FONT, text="", color=0xFFFFFF)

        self.status.anchor_point = (0.5, 0.0)

        self.status.anchored_position = (width // 2, 44)

        self.group.append(self.header)

        self.group.append(self.ip_big)

        self.group.append(self.status)

        self.display.root_group = self.group



    def update(self, hostname: str, ip_addr: str, timestamp: str) -> None:

        self.ip_big.text = ip_addr[:10]

        self.status.text = f"{hostname[:5]} {timestamp[:5]}"



    def cleanup(self) -> None:

        if displayio:

            displayio.release_displays()





def init_backend():

    if OLED_DRIVER == "sh1107":

        return SH1107Display()

    return SSD1312Display()





def main() -> None:

    backend = init_backend()

    hostname = socket.gethostname()

    try:

        while True:

            ip_addr = get_ip_address()

            now = datetime.now().strftime("%H:%M:%S")

            backend.update(hostname, ip_addr, now)  # type: ignore[attr-defined]

            time.sleep(REFRESH_SECONDS)

    except KeyboardInterrupt:

        pass

    finally:

        if hasattr(backend, "cleanup"):

            backend.cleanup()  # type: ignore[attr-defined]





if __name__ == "__main__":

    main()

