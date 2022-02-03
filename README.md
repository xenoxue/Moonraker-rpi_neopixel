# rpi_neopixel for Moonraker
## Description 介绍
This is the standalone repository of the Moonraker RPI neopixel module using Adafruit CircuitPython NeoPixel.

It allows Moonraker to controll on addressable LEDs, such as Neopixels, WS2812 or SK6812 over raspberrypi GPIO pin.

It's compatiable with Klipper's Neopixel module and the Klipper LED Effects module developed by julianschill.

It's compatiable with Fluidd's color palette.


这是一个Moonraker的小插件，可以让moonracker直接驱动插在树莓派GPIO上的Led灯带，支持Neopixels， WS2812 以及SK6812 等常见灯带。

本插件是使用第三方库Adafruit CircuitPython NeoPixel 来驱动灯带的，所以本质上只是一个解决方案，并没有多少核心代码。

本插件兼容Klipper的Neopixel模块，但是创建一个空白的同名的Neopixel灯带。

本插件兼容Klipper的LED Effects灯效插件，巨酷，强烈推荐使用。

本插件兼容Fluidd的调色盘修改灯带颜色。


## Disclaimer 免责声明

This is work in progress and currently in "alpha" state.

仅兴趣开发，目前还在测试阶段，请谨慎使用

缝合的代码，有问题自己解决

## Installation 安装命令
    cd ~
    git clone https://github.com/xenoxue/Moonraker-rpi_neopixel.git
    cd Moonraker-rpi_neopixel
    ./install-rpi_neopixel.sh

## Documentation 使用
Documentation can be found [here](docs/usage.md).

使用文档请点击 [这里](docs/usage.md).

## Wanring 警告
You can only create one rpi_neopixel due to some bug will caused while raspberrypi is controlling multiple strip.
If you have more than one, connect them together and then wire them to your Raspberry Pi using a single connection.

由于树莓派本身硬件上的局限性，是无法同时控制多个灯带。所以本插件仅支持一根led灯带，如果有需要的话，可以考虑将灯带串联起来。

## Credit

- julianschill for [LED Effects for Klipper](https://github.com/julianschill/klipper-led_effect)

- Arksine for [Moonraker](https://github.com/Arksine/moonraker)

- Kevin O'Connor for [Klipper](https://github.com/KevinOConnor/klipper)
