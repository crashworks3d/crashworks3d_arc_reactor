# Arc Reactor -- CW3D / Compass School  (CircuitPython 10.x)

# Libraries: pre-written code that saves us from scratch.
import board
import math
import time
import neopixel

# Constants: change one number here to change the whole animation.
PIXEL_PIN    = board.IO2  # data pin wired to the LED ring
NUM_PIXELS   = 31         # 7-LED center + 24-LED ring = 31 total
CENTER_COUNT = 7          # pixels in the center cluster (first in chain)
OUTER_COUNT  = 24         # pixels in the outer ring
BRIGHTNESS   = 0.35       # global brightness; max 0.4 to save power
SLEEP_MS     = 20         # pause between frames; lower = faster
SWEEP_RATE   = 4.0        # how fast the leading pixel rotates
OUTER_SPEED  = 1.5        # how fast the outer ring breathes
PHASE_STEP   = 0.4        # phase shift between neighboring pixels
CENTER_SPEED = 3.0        # center pulses faster than the ring

# Object: NeoPixel wraps all 31 LEDs in one variable.
# auto_write=False means we control exactly when LEDs update.
pixels = neopixel.NeoPixel(
    PIXEL_PIN, NUM_PIXELS,
    brightness=BRIGHTNESS, auto_write=False)


# Function: one frame of the arc reactor animation.
# pixels = the LED strip object  |  t = current time in seconds
# To swap animations, write a function with the same signature:
#   def my_animation(pixels, t): ...
# then change: animate = my_animation
def arc_reactor(pixels, t):

    # Leading pixel index, stepping around the ring each frame.
    sweep = CENTER_COUNT + int(t * SWEEP_RATE) % OUTER_COUNT

    for i in range(CENTER_COUNT, NUM_PIXELS):
        # Sine wave: smooth 0.0-to-1.0 value, like breathing.
        s = (math.sin(t * OUTER_SPEED + i * PHASE_STEP) + 1) / 2
        if i == sweep:
            pixels[i] = (180, 220, 255)  # bright highlight pixel
        else:
            # R, G, B: three numbers (0-255) mix to make any color.
            r = int(80 * s)
            g = int(160 * s)
            b = int(60 + 195 * s)
            pixels[i] = (r, g, b)

    # Center pulse: faster sine, floor at 0.5 so it stays bright.
    cs = 0.5 + 0.5 * (math.sin(t * CENTER_SPEED) + 1) / 2
    cr = int(160 + 60 * cs)
    cg = int(200 + 40 * cs)
    for i in range(CENTER_COUNT):
        pixels[i] = (cr, cg, 255)  # all 7 center pixels same color


# Helper: converts a 0-255 position into an (r, g, b) rainbow color.
# Imagine a color wheel — 0=red, 85=green, 170=blue, 255=back to red.
# No extra libraries needed; pure math using only multiplication.
def colorwheel(pos):
    pos = pos % 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)       # red → green
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)        # green → blue
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)            # blue → red


# Function: one frame of a rainbow chase animation.
# Every pixel gets a different hue; the whole rainbow shifts each
# frame so it appears to chase around the strip.
def rainbow_chase(pixels, t):

    # offset moves the rainbow forward a little each frame.
    offset = int(t * 50) % 256

    for i in range(NUM_PIXELS):
        # Space hues evenly around the wheel, then shift by offset.
        hue = (offset + i * 256 // NUM_PIXELS) % 256
        pixels[i] = colorwheel(hue)


# Swap this line to use a different animation function.
# Try: animate = rainbow_chase
animate = arc_reactor

t = 0.0  # time counter; grows by one frame each loop

# Main loop: runs forever - this IS the animation.
while True:
    animate(pixels, t)           # fill the pixel buffer for this frame
    pixels.show()                # send the full buffer to LEDs at once
    t += SLEEP_MS / 1000         # advance the time counter one frame
    time.sleep(SLEEP_MS / 1000)  # /1000 converts ms to seconds
