# Moonraker rpi neopixel
For led effect configuaration setup, Please refer to LED_EFFECT usage document: https://github.com/julianschill/klipper-led_effect/blob/master/docs/LED_Effect.md

跑马灯之类的效果请查看LED_EFFECT的相关文档：https://github.com/julianschill/klipper-led_effect/blob/master/docs/LED_Effect.md

# Command 命令
this plugin is compatiable with SET_LED commands.

and TWO addional command was added for direct control(refer to WLED command from Moonraker)

本插件兼容klipper的SET_LED命令，用法可以参考Klipper的相关文档。

另外本插件也添加了2个直接控制的gcode命令，相关代码是抄 Moonraker的WLED 模块。只是把lwed改成rpi_neopixel。所以可以参考下面的文档。

link: https://moonraker.readthedocs.io/en/latest/configuration/
```
  rpi_neopixel strip=case red=1 green=1 blue=1 index=-1
  rpi_neopixel_state
```
# wiring 接线
Please check out this link for full details: https://learn.adafruit.com/neopixels-on-raspberry-pi/raspberry-pi-wiring

## Connect directly to the raspberrypi 直插树莓派并且使用树莓派供电
Pi 5V to NeoPixel 5V

Pi GND to NeoPixel GND

Pi GPIO18 to NeoPixel Din

![image](https://cdn-learn.adafruit.com/assets/assets/000/063/929/original/led_strips_raspi_NeoPixel_bb.jpg?1539981142)

## Using external power with direct connection to the rapsberrypi 直插树莓派但是外部供电
Pi GND to NeoPixel GND

Pi GPIO18 to NeoPixel Din

Power supply ground to NeoPixel GND

Power supply 5V to NeoPixel 5V

![image](https://cdn-learn.adafruit.com/assets/assets/000/063/928/original/led_strips_raspi_NeoPixel_powered_bb.jpg?1539980907)


# Configuration 配置文件

## Standalone Setup 单独使用设置
add the following to Moonraker.conf file

把以下代码添加到Moonraker.conf文件里面去
```
  [rpi_neopixel case]
  chain_count:60
  #   Number of addressable neopixels for use (default: 1)
  initial_preset=-1
  #   Initial preset ID (favourite) to use. If not specified initial_colors
  #   will be used instead.
  initial_red: 0.5
  initial_green: 0.5
  initial_blue: 0.5
  #   Initial colors to use for all neopixels should initial_preset not be set,
  #   initial_white will only be used for RGBW wled strips (defaults: 0.5)
  order: RGB
  #   *** DEPRECATED - Color order is defined per GPIO in WLED directly ***
  #   Color order for WLED strip, RGB or RGBW (default: RGB)
  gpio: 18
  #   Raspberrypi GPIO that is using, NeoPixels must be connected to 10, 12, 18 or 21 to work, 18 is the default pin.
  brightness: 1
```
## Advance Setup 进阶使用设置
this pulgin can be controled as a Klipper Neopixel, By listening to the same name Neopixel color change event, it will allow Fluidd to change its color through webpage, and it can be work as a led_effect chain.

To enable this awesome function, you will need to add a fake Neopixel to your klipper configuration file(printer.cfg).

开启进阶设置的话，需要在Printer.cfg里面加入以下代码，请确保灯带命名保持一致
```
  [neopixel case]
  #   make sure you have exactly the same name as rpi_neopixel, here I'm using "case"
  chain_count:60
  #   the chain_count must be same as rpi_neopixel
  pin:PA7
  #   you have to set a unused pin for Klipper to initailise. it can be any pin, as long as you get no error.
```
