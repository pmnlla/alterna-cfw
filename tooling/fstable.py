import re, sys
from datetime import date

# Rewrite the RSUp partition table from build/fsfollow.
# Table: 7 entries at 0x11C, stride 0x5C. Each entry:
#   base-0x8 : version string (8 bytes, null-terminated, "V"+yymmdd)
#   base+0x0 : offset (LE u32)
#   base+0x4 : size   (LE u32)
# Entry for part N (1_cmdline..7_www) lives at 0x11C+(N-1)*0x5C. 0_RSUP_Header has no slot.
# The version bump forces the on-device updater to flash every partition
# (it version-gates each one; a matching version is skipped).

fsfollow = sys.argv[1] if len(sys.argv) > 1 else "build/fsfollow"
image = sys.argv[2] if len(sys.argv) > 2 else "build/update.bin"

version = ("V" + date.today().strftime("%y%m%d")).encode()  # 8 bytes incl. null pad

with open(image, "r+b") as img:
    for name, off, size in re.findall(r"'(\d+_[^']*)',\s*'([0-9A-Fa-f]+)',\s*'([0-9A-Fa-f]+)'", open(fsfollow).read()):
        n = int(name.split("_")[0])
        if n == 0:
            continue
        base = 0x11C + (n - 1) * 0x5C
        img.seek(base - 8)
        img.write(version.ljust(8, b"\0"))
        img.write(int(off, 16).to_bytes(4, "little"))
        img.write(int(size, 16).to_bytes(4, "little"))
        print(f"{name}: ver {version.decode()} offset 0x{off} size 0x{size} -> ver@0x{base-8:X} field@0x{base:X}")
