# blink_test.py — STORY-001 Hardware Validation
# CW3D Arc Reactor Panel — Compass School
#
# PURPOSE: Validate the complete hardware chain before any animation work.
#          This is NOT the final code.py — it is a diagnostic only.
#
# USAGE:
#   1. Copy this file to the root of the CIRCUITPY drive as "code.py"
#   2. Open serial console (Mu / Thonny / screen) and confirm no import errors
#   3. Watch the board: all 31 pixels should cycle blue → off → blue → off
#   4. Confirm BOTH zones light up:
#        Pixels  0-23 = 24-LED outer ring
#        Pixels 24-30 = 7-LED center cluster
#   5. If all 31 pixels respond cleanly → STORY-001 acceptance criteria met
#
# WIRING REMINDER:
#   ESP32-C3 GPIO2 → 24-LED ring DATA IN
#   24-LED ring DATA OUT → 7-LED center DATA IN
#   Shared 5V (USB VBUS) and GND to both components

import board
import neopixel
import time

NUM_PIXELS = 31       # 24 outer ring + 7 center cluster
PIXEL_PIN = board.IO2 # Single data line — head of the daisy chain
BRIGHTNESS = 0.2      # Keep low during USB-bus-powered bench test

pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS, auto_write=False
)

print("CW3D Arc Reactor — blink test starting")
print(f"Driving {NUM_PIXELS} pixels on {PIXEL_PIN}")

while True:
    pixels.fill((0, 0, 255))  # All pixels blue ON
    pixels.show()
    time.sleep(1)

    pixels.fill((0, 0, 0))    # All pixels OFF
    pixels.show()
    time.sleep(1)
