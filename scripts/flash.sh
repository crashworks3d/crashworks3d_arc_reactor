#!/bin/bash
# flash.sh — Flash CircuitPython + neopixel.mpy + code.py onto ESP32-C3 SuperMini
#
# Usage: ./flash.sh [port]
# Default port: /dev/cu.usbmodem14301
#
# NOTE: The ESP32-C3's internal USB Serial/JTAG controller resets the chip
# into download mode whenever a host opens the serial port (USB_UART_CHIP_RESET).
# Files are installed by building a FAT12 filesystem image and flashing it
# directly alongside the firmware — no serial REPL or CIRCUITPY drive required.
#
# Partition layout (makergo_esp32c3_supermini, 4MB flash):
#   0x000000  CircuitPython firmware
#   0x2d0000  user_fs (FAT12, 0x130000 = 1216KB)
#
# FAT12 filesystem contents:
#   /code.py            arc reactor animation (src/code.py)
#   /lib/neopixel.mpy   NeoPixel driver library

PORT="${1:-/dev/cu.usbmodem14301}"
BIN="bin/adafruit-circuitpython-makergo_esp32c3_supermini-en_US-10.1.4.bin"
NEOPIXEL="bundle/adafruit-circuitpython-bundle-10.x-mpy-20260401/lib/neopixel.mpy"
CODE="src/code.py"
FS_IMAGE="/tmp/cw3d_user_fs.bin"
FS_OFFSET="0x2d0000"
CHIP="esp32c3"
BAUD="460800"

echo "CW3D Arc Reactor — ESP32-C3 Flash Tool"
echo "Port:  $PORT"
echo "Image: $BIN"
echo ""

for f in "$BIN" "$NEOPIXEL" "$CODE"; do
  if [ ! -f "$f" ]; then
    echo "ERROR: $f not found. Run from the project root."
    exit 1
  fi
done

# --- Put board in download mode ---
# CircuitPython disables USB auto-reset, so esptool cannot reset the board
# automatically. The user must manually enter download mode first.
echo "► Put the board in download mode:"
echo "    1. Hold the BOOT button"
echo "    2. Press and release RESET"
echo "    3. Release BOOT"
echo ""
read -rp "  Press Enter when ready..." _

# --- Step 1: Erase ---
echo ""
echo "Step 1: Erasing flash..."
esptool.py --chip "$CHIP" --port "$PORT" --baud "$BAUD" --before no_reset erase_flash
if [ $? -ne 0 ]; then
  echo ""
  echo "ERROR: Erase failed. Make sure the board is in download mode and retry."
  exit 1
fi

# --- Step 2: Write CircuitPython ---
echo ""
echo "Step 2: Writing CircuitPython firmware..."
esptool.py --chip "$CHIP" --port "$PORT" --baud "$BAUD" \
  --before no_reset --after no_reset \
  write_flash -z 0x0 "$BIN"
if [ $? -ne 0 ]; then
  echo ""
  echo "ERROR: Firmware write failed. Check the port and try again."
  exit 1
fi

# --- Step 3: Build FAT12 filesystem image ---
# CircuitPython on ESP32-C3 uses FAT12 (not LittleFS).
# BPB parameters taken directly from a CircuitPython-formatted partition read-back.
#
# Cluster map:
#   2        /lib  directory
#   3-5      /lib/neopixel.mpy  (1325 bytes → 3 clusters)
#   6-7      /code.py           (≤1024 bytes → 2 clusters)
echo ""
echo "Step 3: Building FAT12 filesystem image..."
python3.11 - "$NEOPIXEL" "$CODE" "$FS_IMAGE" <<'PYEOF'
import sys, struct, math

LIB_SRC   = sys.argv[1]
CODE_SRC  = sys.argv[2]
OUT_PATH  = sys.argv[3]

BYTES_PER_SECTOR  = 512
SECTORS_PER_CLUS  = 1
RESERVED_SECTORS  = 1
NUM_FATS          = 1
ROOT_ENT_COUNT    = 512
TOTAL_SECTORS     = 2432
MEDIA             = 0xF8
FAT_SIZE_SECTORS  = 8
SECTORS_PER_TRACK = 63
NUM_HEADS         = 255
HIDDEN_SECTORS    = 1

ROOT_DIR_SECTORS  = (ROOT_ENT_COUNT * 32) // BYTES_PER_SECTOR   # 32
FAT_START_SECTOR  = RESERVED_SECTORS                              # 1
ROOT_DIR_SECTOR   = FAT_START_SECTOR + NUM_FATS * FAT_SIZE_SECTORS  # 9
DATA_START_SECTOR = ROOT_DIR_SECTOR + ROOT_DIR_SECTORS            # 41

img = bytearray(TOTAL_SECTORS * BYTES_PER_SECTOR)

# Boot sector
bs = bytearray(512)
bs[0:3]  = b'\xeb\xfe\x90'
bs[3:11] = b'MSDOS5.0'
struct.pack_into('<H', bs, 11, BYTES_PER_SECTOR)
bs[13] = SECTORS_PER_CLUS
struct.pack_into('<H', bs, 14, RESERVED_SECTORS)
bs[16] = NUM_FATS
struct.pack_into('<H', bs, 17, ROOT_ENT_COUNT)
struct.pack_into('<H', bs, 19, TOTAL_SECTORS)
bs[21] = MEDIA
struct.pack_into('<H', bs, 22, FAT_SIZE_SECTORS)
struct.pack_into('<H', bs, 24, SECTORS_PER_TRACK)
struct.pack_into('<H', bs, 26, NUM_HEADS)
struct.pack_into('<I', bs, 28, HIDDEN_SECTORS)
struct.pack_into('<I', bs, 32, 0)
bs[36] = 0x80; bs[38] = 0x29
struct.pack_into('<I', bs, 39, 0xB3E4338D)
bs[43:54] = b'NO NAME    '
bs[54:62] = b'FAT     '
bs[510] = 0x55; bs[511] = 0xAA
img[0:512] = bs

with open(LIB_SRC, 'rb') as f:
    neo_data = f.read()
with open(CODE_SRC, 'rb') as f:
    code_data = f.read()

neo_clusters  = math.ceil(len(neo_data)  / BYTES_PER_SECTOR)  # 3
code_clusters = math.ceil(len(code_data) / BYTES_PER_SECTOR)  # 2

# Cluster assignments
C_LIB       = 2
C_NEO_START = 3
C_NEO_END   = C_NEO_START + neo_clusters - 1          # 5
C_CODE_START= C_NEO_END + 1                           # 6
C_CODE_END  = C_CODE_START + code_clusters - 1        # 7

# Build FAT12 entries
fat_entries = [0xFF8, 0xFFF]   # indices 0-1 reserved
fat_entries.append(0xFFF)      # index 2: /lib dir (1 cluster, EOF)
for i in range(neo_clusters):  # indices 3..5: neopixel.mpy chain
    c = C_NEO_START + i
    fat_entries.append(c + 1 if i < neo_clusters - 1 else 0xFFF)
for i in range(code_clusters): # indices 6..7: code.py chain
    c = C_CODE_START + i
    fat_entries.append(c + 1 if i < code_clusters - 1 else 0xFFF)

fat = bytearray(FAT_SIZE_SECTORS * BYTES_PER_SECTOR)
for i, val in enumerate(fat_entries):
    off = (i * 3) // 2
    if i % 2 == 0:
        fat[off]   = val & 0xFF
        fat[off+1] = (fat[off+1] & 0xF0) | ((val >> 8) & 0x0F)
    else:
        fat[off]   = (fat[off] & 0x0F) | ((val & 0x0F) << 4)
        fat[off+1] = (val >> 4) & 0xFF
img[FAT_START_SECTOR*512 : FAT_START_SECTOR*512 + len(fat)] = fat

def dir_entry(name83, attr, cluster, size):
    e = bytearray(32)
    e[0:11] = name83.encode().ljust(11)[:11]
    e[11] = attr
    struct.pack_into('<H', e, 22, (2026-1980) << 9 | 4 << 5 | 1)
    struct.pack_into('<H', e, 26, cluster)
    struct.pack_into('<I', e, 28, size)
    return bytes(e)

# Root directory: code.py + lib dir
root = bytearray(ROOT_DIR_SECTORS * 512)
root[0:32]  = dir_entry('CODE    PY ', 0x20, C_CODE_START, len(code_data))
root[32:64] = dir_entry('LIB        ', 0x10, C_LIB, 0)
img[ROOT_DIR_SECTOR*512 : ROOT_DIR_SECTOR*512 + len(root)] = root

# Cluster 2: /lib directory
lib_dir = bytearray(512)
lib_dir[0:32]  = dir_entry('.          ', 0x10, C_LIB, 0)
lib_dir[32:64] = dir_entry('..         ', 0x10, 0, 0)
lib_dir[64:96] = dir_entry('NEOPIXELMPY', 0x20, C_NEO_START, len(neo_data))
c2 = DATA_START_SECTOR * 512
img[c2 : c2 + 512] = lib_dir

# Clusters 3+: neopixel.mpy
neo_padded = neo_data + bytes(neo_clusters * 512 - len(neo_data))
c3 = c2 + 512
img[c3 : c3 + neo_clusters * 512] = neo_padded

# Clusters 6+: code.py
code_padded = code_data + bytes(code_clusters * 512 - len(code_data))
c6 = c3 + neo_clusters * 512
img[c6 : c6 + code_clusters * 512] = code_padded

with open(OUT_PATH, 'wb') as f:
    f.write(img)

print(f"  /code.py           ({len(code_data)} bytes)")
print(f"  /lib/neopixel.mpy  ({len(neo_data)} bytes)")
print(f"  Image: {len(img)} bytes (0x{len(img):x}) → {OUT_PATH}")
PYEOF

if [ $? -ne 0 ]; then
  echo ""
  echo "ERROR: Failed to build filesystem image."
  exit 1
fi

# --- Step 4: Flash filesystem image ---
echo ""
echo "Step 4: Writing FAT12 filesystem to $FS_OFFSET..."
esptool.py --chip "$CHIP" --port "$PORT" --baud "$BAUD" \
  --before no_reset --after hard_reset \
  write_flash "$FS_OFFSET" "$FS_IMAGE"
if [ $? -ne 0 ]; then
  echo ""
  echo "ERROR: Filesystem write failed."
  exit 1
fi

echo ""
echo "✓ Done! Board flashed with:"
echo "    CircuitPython 10.1.4 (makergo_esp32c3_supermini)"
echo "    /code.py"
echo "    /lib/neopixel.mpy"
echo ""
echo "Unplug and connect to a USB-C charger to run the animation."
