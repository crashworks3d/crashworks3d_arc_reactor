#!/usr/bin/env python3
"""
flash.py -- Cross-platform flash tool for CW3D Arc Reactor
Works on macOS, Linux, and Windows (no bash required).

Usage:
    python scripts/flash.py [port]

Default ports:
    macOS:   /dev/cu.usbmodem14301
    Linux:   /dev/ttyUSB0
    Windows: COM3

Requirements:
    pip install esptool
"""

import math
import os
import struct
import subprocess
import sys
import tempfile

# -- File paths (resolved relative to this script's location) -----------
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT        = os.path.dirname(SCRIPTS_DIR)

BIN      = os.path.join(ROOT, 'bin',
           'adafruit-circuitpython-makergo_esp32c3_supermini'
           '-en_US-10.1.4.bin')
NEOPIXEL = os.path.join(ROOT, 'bundle',
           'adafruit-circuitpython-bundle-10.x-mpy-20260401',
           'lib', 'neopixel.mpy')
CODE     = os.path.join(ROOT, 'src', 'code.py')
FS_IMAGE = os.path.join(tempfile.gettempdir(), 'cw3d_user_fs.bin')

# -- Flash parameters ---------------------------------------------------
CHIP      = 'esp32c3'
BAUD      = '460800'
FS_OFFSET = '0x2d0000'


def default_port():
    if sys.platform == 'win32':
        return 'COM3'
    elif sys.platform == 'darwin':
        return '/dev/cu.usbmodem14301'
    else:
        return '/dev/ttyUSB0'


def esptool_cmd(port, *args):
    """Build an esptool command using the current Python interpreter."""
    return [sys.executable, '-m', 'esptool',
            '--chip', CHIP, '--port', port, '--baud', BAUD] + list(args)


def run(cmd, label):
    """Print label, run command, exit on failure."""
    print(f'\n{label}')
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f'\nERROR: {label} failed.')
        sys.exit(1)


def build_fs_image(neo_path, code_path, out_path):
    """Build a FAT12 filesystem image with code.py and lib/neopixel.mpy.

    BPB parameters match a CircuitPython-formatted ESP32-C3 partition.
    Partition layout: user_fs at 0x2d0000, size 0x130000 (1,245,184 bytes).
    """
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

    ROOT_DIR_SECTORS  = (ROOT_ENT_COUNT * 32) // BYTES_PER_SECTOR  # 32
    FAT_START_SECTOR  = RESERVED_SECTORS                            # 1
    ROOT_DIR_SECTOR   = FAT_START_SECTOR + NUM_FATS * FAT_SIZE_SECTORS  # 9
    DATA_START_SECTOR = ROOT_DIR_SECTOR + ROOT_DIR_SECTORS          # 41

    img = bytearray(TOTAL_SECTORS * BYTES_PER_SECTOR)

    # Boot sector (BPB)
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
    bs[36] = 0x80
    bs[38] = 0x29
    struct.pack_into('<I', bs, 39, 0xB3E4338D)
    bs[43:54] = b'NO NAME    '
    bs[54:62] = b'FAT     '
    bs[510] = 0x55
    bs[511] = 0xAA
    img[0:512] = bs

    with open(neo_path, 'rb') as f:
        neo_data = f.read()
    with open(code_path, 'rb') as f:
        code_data = f.read()

    neo_clusters  = math.ceil(len(neo_data)  / BYTES_PER_SECTOR)
    code_clusters = math.ceil(len(code_data) / BYTES_PER_SECTOR)

    # Cluster assignments: 2=lib dir, 3+=neopixel.mpy, then code.py
    C_LIB        = 2
    C_NEO_START  = 3
    C_NEO_END    = C_NEO_START + neo_clusters - 1
    C_CODE_START = C_NEO_END + 1

    fat_entries = [0xFF8, 0xFFF, 0xFFF]   # clusters 0-1 reserved, 2=lib
    for i in range(neo_clusters):
        nxt = C_NEO_START + i + 1 if i < neo_clusters - 1 else 0xFFF
        fat_entries.append(nxt)
    for i in range(code_clusters):
        nxt = C_CODE_START + i + 1 if i < code_clusters - 1 else 0xFFF
        fat_entries.append(nxt)

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

    # Root directory: code.py + lib/
    root = bytearray(ROOT_DIR_SECTORS * 512)
    root[0:32]  = dir_entry('CODE    PY ', 0x20, C_CODE_START, len(code_data))
    root[32:64] = dir_entry('LIB        ', 0x10, C_LIB, 0)
    img[ROOT_DIR_SECTOR*512 : ROOT_DIR_SECTOR*512 + len(root)] = root

    # Cluster 2: lib/ directory entries
    lib_dir = bytearray(512)
    lib_dir[0:32]  = dir_entry('.          ', 0x10, C_LIB, 0)
    lib_dir[32:64] = dir_entry('..         ', 0x10, 0, 0)
    lib_dir[64:96] = dir_entry('NEOPIXELMPY', 0x20, C_NEO_START, len(neo_data))
    c2 = DATA_START_SECTOR * 512
    img[c2 : c2 + 512] = lib_dir

    # neopixel.mpy data
    neo_padded = neo_data + bytes(neo_clusters * 512 - len(neo_data))
    c3 = c2 + 512
    img[c3 : c3 + neo_clusters * 512] = neo_padded

    # code.py data
    code_padded = code_data + bytes(code_clusters * 512 - len(code_data))
    c6 = c3 + neo_clusters * 512
    img[c6 : c6 + code_clusters * 512] = code_padded

    with open(out_path, 'wb') as f:
        f.write(img)

    print(f'  /code.py           ({len(code_data)} bytes)')
    print(f'  /lib/neopixel.mpy  ({len(neo_data)} bytes)')
    print(f'  Image: {len(img)} bytes -> {out_path}')


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else default_port()

    print('CW3D Arc Reactor -- Cross-Platform Flash Tool')
    print(f'Port:  {port}')
    print(f'Image: {os.path.basename(BIN)}')
    print()

    for f in [BIN, NEOPIXEL, CODE]:
        if not os.path.isfile(f):
            print(f'ERROR: {f}')
            print('       File not found. Run from the project root.')
            sys.exit(1)

    print('Put the board in download mode:')
    print('  1. Hold the BOOT button')
    print('  2. Press and release RESET')
    print('  3. Release BOOT')
    print()
    input('  Press Enter when ready...')

    run(esptool_cmd(port, '--before', 'no_reset', 'erase_flash'),
        'Step 1: Erasing flash...')

    run(esptool_cmd(port, '--before', 'no_reset', '--after', 'no_reset',
                    'write_flash', '-z', '0x0', BIN),
        'Step 2: Writing CircuitPython firmware...')

    print('\nStep 3: Building FAT12 filesystem image...')
    build_fs_image(NEOPIXEL, CODE, FS_IMAGE)

    run(esptool_cmd(port, '--before', 'no_reset', '--after', 'hard_reset',
                    'write_flash', FS_OFFSET, FS_IMAGE),
        f'Step 4: Writing FAT12 filesystem to {FS_OFFSET}...')

    print()
    print('Done! Board flashed with:')
    print('  CircuitPython 10.1.4 (makergo_esp32c3_supermini)')
    print('  /code.py')
    print('  /lib/neopixel.mpy')
    print()
    print('Unplug and connect to a USB-C charger to run the animation.')


if __name__ == '__main__':
    main()
