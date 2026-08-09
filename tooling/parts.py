class FirmwarePart:
    def __init__(self, name, offset, size):
        self.name = name
        self.offset = offset
        self.size = size

# here's something noteworthy!
# add a number to indicate which part goes where.
# therefore, the reasembly process can automatically figure out "okay, this goes after that."
# oh and it also needs it defined since it's a 1 line cat command and REALLY stupid.
# i'll tag the files properly eventually

parts_dummy = [
    FirmwarePart("Nil", 0, 0),
    FirmwarePart('Nil', 0, 0)
]

parts_2104 = [
    # instead of binwalk, i went ahead and worked on decoding the inbuilt partition table in the RSUp header, following the magic string @ 0x00 
    FirmwarePart("0_RSUP_Header", 0x0, 0x398),
    FirmwarePart("1_cmdline", 0x398, 0x200),
    FirmwarePart("2_binary_1", 0x598, 0x3dc4c),
    FirmwarePart("3_kernel", 0x3E1E4, 0x255a38),
    FirmwarePart("4_Squashfs_rootfs", 0x293C1C, 0x2EA000),
    FirmwarePart("5_Squashfs_app", 0x57DC1C, 0x957000),
    FirmwarePart("6_bootlogo.jpg", 0xED4C1C, 0x8CE9),
    FirmwarePart("7_Squashfs_www", 0xEDD905, 0x48a000),
]
parts_2108 = [
    # instead of binwalk, i went ahead and worked on decoding the inbuilt partition table in the RSUp header, following the magic string @ 0x00 
    FirmwarePart("0_RSUP_Header", 0x0, 0x398),
    FirmwarePart("1_cmdline", 0x398, 0x200),
    FirmwarePart("2_binary_1", 0x598, 0x3E774),
    FirmwarePart("3_kernel", 0x03ED0C, 0x255A38),
    FirmwarePart("4_Squashfs_rootfs", 0x294744, 0x2EA000),
    FirmwarePart("5_Squashfs_app", 0x57E744, 0x957000),
    FirmwarePart("6_bootlogo.jpg", 0xEA9744, 0x8CE9),
    FirmwarePart("7_Squashfs_www", 0xEB242D, 0x48a000),
]
