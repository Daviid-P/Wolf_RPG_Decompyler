# Wolf RPG Decompiler

I made this because I wanted a way to decompile `.wolf` files.

`.wolf` files are files and directories archived with [DXLib](https://dxlib.xsrv.jp/dxdload.html) by the software [Wolf RPG Editor](https://www.silversecond.com/WolfRPGEditor/Download.html) a software developed by SmokingWOLF to make RPG games.

They might be compressed and/or encrypted.

As of time of writing DXLib is at version 3.23 and has had 8 archive versions.

- From v1 to v6 the encryption key can be up to 12 bytes long.
- On v7 the encryption key can be up to 32 bytes long.
- On v8 the encryption key can be up to 56 bytes long.

As of time of writing Wolf RPG Editor is at version 2.81 and has had 4 default encryption keys.

- From v1.01 to v2.02a the key is `0F 53 E1 3E 04 37 12 17 60 0F 53 E1`
- On v2.10 the key is `4C D9 2A B7 28 9B AC 07 3E 77 EC 4C`
- From v2.20 to v2.24 the key is `38 50 40 28 72 4F 21 70 3B 73 35 38` or `8P@(rO!p;s5`
- From v2.255 to 2.281 the key is `57 4C 46 52 50 72 4F 21 70 28 3B 73 35 28 28 38 50 40 28 28 55 46 57 6C 75 24 23 35 28 3D` or `WLFRPrO!p(;s5((8P@((UFWlu$#5(=`

<sub>NOTE: The hexadecimal keys on the source below are the output of the `keyCreate` function</sub>

Wolf RPG Editor has used versions 5, 6 and 8 of the DXLib Archiver.

----

Keep in mind that I only made this to decompile, so all functions related to compiling/encoding are missing.

----

Sources
-----
- [DXArchive Format and Keys](http://wiki.xentax.com/index.php/DX_Archive)
- [DXLib](https://dxlib.xsrv.jp/dxdload.html)
- [Wolf RPG Editor](https://www.silversecond.com/WolfRPGEditor/Download.html)