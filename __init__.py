from pathlib import Path
from . import DXArchive
from . import DXArchive5
from . import DXArchive6

__all__ = ["decompile_wolf"]

key_1_01_2_02 = bytearray(
    [0x0F, 0x53, 0xE1, 0x3E, 0x04, 0x37, 0x12, 0x17, 0x60, 0x0F, 0x53, 0xE1]
)
key_2_10 = bytearray(
    [0x4C, 0xD9, 0x2A, 0xB7, 0x28, 0x9B, 0xAC, 0x07, 0x3E, 0x77, 0xEC, 0x4C]
)
key_2_20_2_24 = bytearray(b"8P@(rO!p;s58")
key_2_25_2_81 = bytearray(b"WLFRPrO!p(;s5((8P@((UFWlu$#5(=")

decompiler_pairs = [
    (DXArchive5.DXArchive(), key_1_01_2_02),
    (DXArchive5.DXArchive(), key_2_10),
    (DXArchive6.DXArchive(), key_2_20_2_24),
    (DXArchive.DXArchive(), key_2_25_2_81),
]


def decompile_wolf(archivePath: Path) -> bool:
    for pair in decompiler_pairs:
        decompiler = pair[0]
        key = pair[1]
        decompiled = decompiler.decodeArchive(
            archivePath=archivePath,
            outputPath=archivePath.parent / Path("decompiled_temp"),
            only_game_dat=True,
            keyString_=key,
        )
        if decompiled:
            break
    return decompiled
