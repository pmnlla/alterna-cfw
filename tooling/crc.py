import argparse
from enum import Enum
import zlib
import shutil
from parts import *
import sys

uImageLocation = 0x1234

class Endianess(Enum):
    BIG = 'big'
    LITTLE = 'little'

class Checksum:
    def __init__(self, endian: Endianess, location: int):
        self.endian = endian
        self.location = location
        self.value = 0
    def Generate(self, path: str):
        return 0x00000000 # default value
    def Inject(self, filepath: str):
        try:
            shutil.copy(filepath, filepath + ".signed")
            with open(filepath + ".signed", "r+b") as image:
                image.seek(self.location)
                old_sum = image.read(4)
                new_sum = self.Generate(path=filepath)
                image.seek(self.location)
                image.write(new_sum.to_bytes(4,byteorder=self.endian.value))
                print(f"Replaced {old_sum.hex()} with {hex(new_sum)} at {hex(self.location)}")
        except Exception as e:
            raise(e)

# currently only target 2104
class UImageBodyChecksum(Checksum):
    def __init__(self):
        super().__init__(Endianess.BIG, (uImageLocation + 0x18)) # 4 is the offset w/in the umage header for the header checksum
    def Generate(self, path: str):
        try:
            with open(path, "rb") as image:
                image.seek(self.location - 0x18 + 0x0C)
                size = int.from_bytes(image.read(4), "big")
                image.seek(self.location + (64 - 0x18))
                data = image.read(size)
                csum = zlib.crc32(data)
                print(f"Body csum = {hex(csum)}")
                return csum
        except Exception as e:
            raise(e)
            return 0x00000000

class UImageHeaderChecksum(Checksum):
    def __init__(self):
        super().__init__(Endianess.BIG, (uImageLocation  + 0x4)) # 18 is the offset for body checksum
    def Generate(self, path: str):
        try:
            with open(path, "rb") as image:
                image.seek(self.location - 0x4) # end of header
                data = bytearray(image.read(64))
                crcLength = 4
                crcStart = 4
                data[crcStart:(crcStart+crcLength)] = b'\x00' * crcLength # always going to be 4. why did i bother?
                csum = zlib.crc32(data)
                print(f"Header csum = {hex(csum)}")
                return csum
        except Exception as e:
            raise(e)
            return 0x00000000
        
# this part, gpt-5.5 figured out. how? i have no idea. ive also learned not to ask, since it sucks at making shit understandable.
class RaysharpHeaderChechsum(Checksum):
    def __init__(self):
        super().__init__(Endianess.LITTLE, (0x4)) 
    def Generate(self, path: str):
        try:
            with open(path, "rb") as image:
                data = bytearray(image.read()) # all the way until the end
                crcLength = 4
                crcStart = 4
                data[crcStart:(crcStart+crcLength)] = b'' # remove and concatenate!
                csum = zlib.crc32(data, 0xFFFFFFFF) ^ 0xFFFFFFFF # init = 0 here, not 0xFFFFFFF)
                print(f"RSUp csum = {hex(csum)}")
                return csum
        except Exception as e:
            raise(e)
            return 0x0000000

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='Raysharp CRC32 signed',
                    description='Signs RSUp OTA images for the LHA2104 series',
                    epilog='wub wub')
    parser.add_argument('-i', '--inject',
                    action='store_true')  # on/off flag
    parser.add_argument('-f', '--filename')
    parser.add_argument('-m', '--model')
    args = parser.parse_args()

    parts = parts_dummy
    if args.model == "2104":
        parts = parts_2104
    elif args.model == "2108":
        parts = parts_2108
    else:
        print("No model identified!")
        sys.exit(1)
    kernel = next(p for p in parts if p.name.endswith("_kernel"))
    uImageLocation = kernel.offset
    checksums = [
        UImageBodyChecksum(),
        UImageHeaderChecksum(),
        RaysharpHeaderChechsum()
    ]
    for i in checksums:
        if args.inject:
            i.Inject(filepath = args.filename)
        else:
            i.Generate(path = args.filename)