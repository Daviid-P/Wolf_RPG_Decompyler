from io import SEEK_SET, TextIOWrapper
from pathlib import Path
from stat import FILE_ATTRIBUTE_DIRECTORY
import struct
import array


DXA_HEAD = struct.unpack("H", b"DX")[0]  # Header
DXA_VER = 0x0006  # Version
DXA_BUFFERSIZE = 0x1000000  # Size of the buffer used when creating the archive
DXA_KEY_STRING_LENGTH = 12  # Length of key string

# Default key string
defaultKeyString = bytearray(
    [0x44, 0x58, 0x42, 0x44, 0x58, 0x41, 0x52, 0x43, 0x00]
)  # "DXLIBARC"

# Length of the log string
logStringLength = 0


class DARC_HEAD:
    head = None  # Header
    version = None  # Version
    headSize = None  # Total size of the file without the DARC_HEAD header information.
    dataStartAddress = None  # The data address where the data of the first file is stored (the first address of the file is assumed to be address 0)
    fileNameTableStartAddress = None  # The first address of the file name table (the first address of the file is assumed to be address 0)
    fileTableStartAddress = None  # First address of the file table (assumes the address of the member variable FileNameTableStartAddress to be 0)
    directoryTableStartAddress = None  # First address of the directory table (assumes the address of the member variable FileNameTableStartAddress to be 0)
    # The DARC_DIRECTORY structure located at address 0 is the root directory.
    charCodeFormat = None  # Code page number used for the file name

    def __init__(self, header_bytes=None):
        if header_bytes is None:
            return
        unpacked = struct.unpack("HHIQQQQQ", header_bytes)
        self.head = unpacked[0]
        self.version = unpacked[1]
        self.headSize = unpacked[2]
        self.dataStartAddress = unpacked[3]
        self.fileNameTableStartAddress = unpacked[4]
        self.fileTableStartAddress = unpacked[5]
        self.directoryTableStartAddress = unpacked[6]
        self.charCodeFormat = unpacked[7]

    def __len__(self) -> int:
        return struct.calcsize("HHIQQQQQ")

    def __repr__(self) -> str:
        return f"""
Head->head = {self.head}
Head->self.version = {self.version}
Head->headSize = {self.headSize}
Head->dataStartAddress = {self.dataStartAddress}
Head->fileNameTableStartAddress = {self.fileNameTableStartAddress}
Head->fileTableStartAddress = {self.fileTableStartAddress}
Head->directoryTableStartAddress = {self.directoryTableStartAddress}
Head->charCodeFormat = {self.charCodeFormat}
"""


# Time information of the file
class DARC_FILETIME:
    create = None  # Creation time
    lastAccess = None  # Last access time
    lastWrite = None  # Last update time

    def __init__(self, fileTime_bytes=None):
        if fileTime_bytes is None:
            return
        unpacked = struct.unpack("QQQ", fileTime_bytes[: len(self)])
        self.create = unpacked[0]
        self.lastAccess = unpacked[1]
        self.lastWrite = unpacked[2]

    def __len__(self) -> int:
        return struct.calcsize("QQQ")

    def __repr__(self) -> str:
        return f"""\tTime->create = {self.create}
\tTime->lastAccess = {self.lastAccess}
\tTime->lastWrite = {self.lastWrite}"""


# File storage information
class DARC_FILEHEAD:
    nameAddress = None  # Address where the file name is stored (the address of the member variable FileNameTableStartAddress of the ARCHIVE_HEAD structure is set to address 0)
    attributes = None  # File attributes
    time = None  # Time information
    dataAddress = None  # Address where the file is stored.
    #            In the case of a file, the address indicated by the member variable DataStartAddress of the DARC_HEAD structure shall be address 0.
    #            In the case of a directory: The address indicated by the member variable "DirectoryTableStartAddress" of the DARC_HEAD structure shall be set to address 0.
    dataSize = None  # Data size of the file
    pressDataSize = None  # The size of the data after compression ( 0xffffffffffffffffff: not compressed ) (added in Ver0x0002)

    def __init__(self, fileHead_bytes=None):
        if fileHead_bytes is None:
            return

        unpacked = struct.unpack("QQQQQQQQ", fileHead_bytes[: len(self)])
        self.nameAddress = unpacked[0]
        self.attributes = unpacked[1]
        self.time = DARC_FILETIME()
        self.time.create = unpacked[2]
        self.time.lastAccess = unpacked[3]
        self.time.lastWrite = unpacked[4]
        self.dataAddress = unpacked[5]
        self.dataSize = unpacked[6]
        self.pressDataSize = unpacked[7]

    def __len__(self) -> int:
        return struct.calcsize("QQQQQQQQ")

    def __repr__(self) -> str:
        return f"""File->nameAddress = {self.nameAddress}
File->attributes = {self.attributes}
File->time.create = {self.time.create}
File->time.lastAccess = {self.time.lastAccess}
File->time.lastWrite = {self.time.lastWrite}
File->dataAddress = {self.dataAddress}
File->dataSize = {self.dataSize}
File->pressDataSize = {self.pressDataSize}"""


# Directory storage information
class DARC_DIRECTORY:
    directoryAddress = None  # Address where my DARC_FILEHEAD is stored (Address 0 is the address indicated by the member variable FileTableStartAddress of the DARC_HEAD structure)
    parentDirectoryAddress = None  # The address where DARC_DIRECTORY of the parent directory is stored ( The address indicated by the member variable DirectoryTableStartAddress of the DARC_HEAD structure is set to address 0.)
    fileHeadNum = None  # Number of files in the directory
    fileHeadAddress = None  # The address where the header column of the file in the directory is stored ( The address indicated by the member variable FileTableStartAddress of the DARC_HEAD structure is set to address 0.)

    def __init__(self, directory_bytes=None):
        if directory_bytes is None:
            return
        unpacked = struct.unpack("QQQQ", directory_bytes[: len(self)])
        self.directoryAddress = unpacked[0]
        self.parentDirectoryAddress = unpacked[1]
        self.fileHeadNum = unpacked[2]
        self.fileHeadAddress = unpacked[3]

    def __len__(self) -> int:
        return struct.calcsize("QQQQ")

    def __repr__(self) -> str:
        return f"""
self.directoryAddress = {self.directoryAddress}
self.parentDirectoryAddress = {self.parentDirectoryAddress}
self.fileHeadNum = {self.fileHeadNum}
self.fileHeadAddress = {self.fileHeadAddress}
"""


# Information for storing the progress of the encoding process
class DARC_ENCODEINFO:
    totalFileNum = None  # Total number of files
    compFileNum = None  # Number of files processed.
    prevDispTime = None  # Time of the last status output
    processFileName = None  # Name of the file currently being processed
    outputStatus = None  # Whether status output is performed or not

    def __repr__(self) -> str:
        return f"""
self.totalFileNum = {self.totalFileNum}
self.compFileNum = {self.compFileNum}
self.prevDispTime = {self.prevDispTime}
self.processFileName = {self.processFileName}
self.outputStatus = {self.outputStatus}
"""


class DXArchive:
    MIN_COMPRESS = 4  # Minimum number of compressed bytes
    MAX_SEARCHLISTNUM = (
        64  # Maximum number of lists to traverse to find the maximum match length
    )
    MAX_SUBLISTNUM = 65536  # Maximum number of sublists to reduce compression time
    MAX_COPYSIZE = (
        0x1FFF + MIN_COMPRESS
    )  # Maximum size to copy from a reference address ( Maximum copy size that a compression code can represent + Minimum number of compressed bytes )
    MAX_ADDRESSLISTNUM = 1024 * 1024 * 1  # Maximum size of slide dictionary
    MAX_POSITION = 1 << 24  # Maximum relative address that can be referenced ( 16MB )

    def __init__(self) -> None:
        pass

    def error(self) -> bool:
        if self.fp is not None:
            self.fp.close()

        return False

    def decodeArchive(
        self,
        archivePath: Path,
        outputPath: Path = Path("."),
        only_game_dat: bool = False,
        keyString_: bytearray = None,
    ):
        self.fp = open(archivePath, mode="rb")
        self.outputPath = outputPath
        self.directory = self.outputPath
        self.only_game_dat = only_game_dat

        key = bytearray([0] * (DXA_KEY_STRING_LENGTH))

        # 鍵の作成
        key = self.keyCreate(keyString_, key)

        head = self.keyConvFileRead(None, len(DARC_HEAD()), self.fp, key, 0)

        head = DARC_HEAD(head)

        if head.head != DXA_HEAD:
            return self.error()

        if head.version != DXA_VER:
            return self.error()

        headBuffer = array.array("B", [0] * head.headSize)

        if head.headSize is None or head.headSize == 0:
            return self.error()

        self.fp.seek(head.fileNameTableStartAddress, SEEK_SET)

        headBuffer = self.keyConvFileRead(headBuffer, head.headSize, self.fp, key, 0)

        nameP = headBuffer
        fileP = nameP[head.fileTableStartAddress :]
        dirP = nameP[head.directoryTableStartAddress :]
        self.directoryDecode(
            nameP, dirP, fileP, head, DARC_DIRECTORY(dirP), self.fp, key
        )
        self.fp.close()
        return True

    def keyCreate(self, source: bytearray, key: bytearray):

        key_length = len(key)

        if source is None:
            for i in range(key_length):
                key[i] = 0xAAAAAAAA
        else:
            tmp = source * max(1, DXA_KEY_STRING_LENGTH % key_length)
            key = tmp[:DXA_KEY_STRING_LENGTH]

        key[0] = (~key[0]) % 256
        key[1] = ((key[1] >> 4) | (key[1] << 4)) % 256
        key[2] = (key[2] ^ 0x8A) % 256
        key[3] = (~((key[3] >> 4) | (key[3] << 4))) % 256
        key[4] = (~key[4]) % 256
        key[5] = (key[5] ^ 0xAC) % 256
        key[6] = (~key[6]) % 256
        key[7] = (~((key[7] >> 3) | (key[7] << 5))) % 256
        key[8] = ((key[8] >> 5) | (key[8] << 3)) % 256
        key[9] = (key[9] ^ 0x7F) % 256
        key[10] = (((key[10] >> 4) | (key[10] << 4)) ^ 0xD6) % 256
        key[11] = (key[11] ^ 0xCC) % 256

        return key

    def keyConvFileRead(
        self,
        data: bytearray,
        size: int,
        fp: TextIOWrapper,
        key: bytearray,
        position: int = -1,
    ) -> bytearray:
        pos = 0

        # ファイルの位置を取得しておく
        if position == -1:
            pos = fp.tell()
        else:
            pos = position

        # 読み込む
        data = bytearray(fp.read(size))  # For assignment in keyConv data[i] ^= key[j]

        data = self.keyConv(data, size, pos, key)

        return data

    def keyConv(
        self, data: bytearray, size: int, position: int, key: bytearray
    ) -> bytearray:
        position %= DXA_KEY_STRING_LENGTH

        j = position
        for i in range(size):
            data[i] ^= key[j]
            j += 1
            if j == DXA_KEY_STRING_LENGTH:
                j = 0

        return data

    def decode(self, src, dest) -> tuple:
        srcp = src

        destsize = struct.unpack("I", srcp[0:4])[0]
        srcsize = struct.unpack("I", srcp[4:8])[0] - 9

        keycode = srcp[8]

        if dest is None:
            return destsize

        sp = srcp[9:]

        tda = bytearray([0] * (destsize))
        tdac = 0

        while srcsize > 0:
            if sp[0] != keycode:
                tda[tdac] = sp[0]
                tdac += 1
                sp = sp[1:]
                srcsize -= 1
                continue

            if sp[1] == keycode:
                tda[tdac] = keycode % 256
                tdac += 1
                sp = sp[2:]
                srcsize -= 2
                continue

            code = sp[1]

            if code > keycode:
                code -= 1

            sp = sp[2:]
            srcsize -= 2

            conbo = code >> 3
            if code & (0x1 << 2):
                conbo |= sp[0] << 5
                sp = sp[1:]
                srcsize -= 1

            conbo += self.MIN_COMPRESS

            indexsize = code & 0x3
            if indexsize == 0:
                index = sp[0]
                sp = sp[1:]
                srcsize -= 1
            elif indexsize == 1:
                index = struct.unpack("H", sp[0:2])[0]
                sp = sp[2:]
                srcsize -= 2
            elif indexsize == 2:
                index = struct.unpack("H", sp[0:2])[0] | (sp[2] << 16)
                sp = sp[3:]
                srcsize -= 3

            index += 1

            if index < conbo:
                num = index
                while conbo > num:
                    copied_bytes = tda[tdac - num : tdac - num + num]
                    tda[tdac : tdac + num] = copied_bytes
                    tdac += num
                    conbo -= num
                    num += num
                if conbo != 0:
                    copied_bytes = tda[tdac - num : tdac - num + conbo]
                    tda[tdac : tdac + conbo] = copied_bytes
                    tdac += conbo
            else:
                copied_bytes = tda[tdac - index : tdac - index + conbo]
                tda[tdac : tdac + conbo] = copied_bytes
                tdac += conbo

        return (tda, destsize)

    def directoryDecode(
        self, nameP, dirP, fileP, head: DARC_HEAD, _dir: DARC_DIRECTORY, arcP, key
    ) -> None:
        old_directory = self.directory

        if (
            _dir.directoryAddress != 0xFFFFFFFFFFFFFFFF
            and _dir.parentDirectoryAddress != 0xFFFFFFFFFFFFFFFF
        ):
            dirFile = DARC_FILEHEAD(fileP[_dir.directoryAddress :])
            pName = self.getOriginalFileName(nameP[dirFile.nameAddress :])
            self.directory = self.directory / pName
            self.directory.mkdir(parents=True, exist_ok=True)

        fileHeadSize = len(DARC_FILEHEAD())
        file = DARC_FILEHEAD(fileP[_dir.fileHeadAddress :])
        last_index = _dir.fileHeadAddress
        for i in range(_dir.fileHeadNum):
            if file.attributes & FILE_ATTRIBUTE_DIRECTORY:
                # ディレクトリの場合は再帰をかける
                self.directoryDecode(
                    nameP,
                    dirP,
                    fileP,
                    head,
                    DARC_DIRECTORY(dirP[file.dataAddress :]),
                    arcP,
                    key,
                )
                if self.only_game_dat:
                    if "BasicData" not in str(self.directory):
                        last_index += fileHeadSize
                        file = DARC_FILEHEAD(fileP[last_index:])
                        continue
            else:
                # ファイルの場合は展開する

                # バッファを確保する
                buffer = bytearray([0] * (DXA_BUFFERSIZE))
                if buffer is None or len(buffer) == 0:
                    return -1

                # ファイルを開く
                pName = self.getOriginalFileName(nameP[file.nameAddress :])
                if self.only_game_dat:
                    if str(pName) != "Game.dat":
                        last_index += fileHeadSize
                        file = DARC_FILEHEAD(fileP[last_index:])
                        continue

                if not self.directory.exists():
                    self.directory.mkdir(parents=True)
                destP = open(self.directory / pName, mode="wb")

                # データがある場合のみ転送
                if file.dataSize != 0:
                    # 初期位置をセットする
                    if arcP.tell() != head.dataStartAddress + file.dataAddress:
                        arcP.seek(head.dataStartAddress + file.dataAddress, SEEK_SET)

                    if head.version >= 2 and file.pressDataSize != 0xFFFFFFFFFFFFFFFF:
                        # 圧縮データが収まるメモリ領域の確保
                        temp = bytearray([0] * (file.pressDataSize + file.dataSize))

                        if head.version >= 5:
                            read = self.keyConvFileRead(
                                temp, file.pressDataSize, arcP, key, file.dataSize
                            )
                        else:
                            read = self.keyConvFileRead(
                                temp, file.pressDataSize, arcP, key
                            )

                        temp[: len(read)] = read

                        # 解凍
                        (decoded, _) = self.decode(temp, temp[file.pressDataSize :])
                        temp[file.pressDataSize :] = decoded

                        # 書き出し
                        destP.write(
                            temp[
                                file.pressDataSize : file.pressDataSize + file.dataSize
                            ]
                        )
                    else:
                        # 転送処理開始
                        writeSize = 0
                        while writeSize < file.dataSize:
                            if file.dataSize - writeSize > DXA_BUFFERSIZE:
                                moveSize = DXA_BUFFERSIZE
                            else:
                                moveSize = file.dataSize - writeSize

                            if head.version >= 5:
                                read = self.keyConvFileRead(
                                    buffer,
                                    moveSize,
                                    arcP,
                                    key,
                                    file.dataSize + writeSize,
                                )
                            else:
                                read = self.keyConvFileRead(buffer, moveSize, arcP, key)

                            buffer[: len(read)] = read

                            # 書き出し
                            destP.write(buffer[:moveSize])

                            writeSize += moveSize

                # ファイルを閉じる
                destP.close()

                """
                # This is on the original .cpp file so I copied it too but I'm pretty sure the dates are wrongly parsed
                # ファイルのタイムスタンプを設定する
                import win32file, pywintypes
                
                pName = self.getOriginalFileName(nameP[file.nameAddress:])
                
                hFile = win32file.CreateFileW(str(self.directory / pName),
                                    win32file.GENERIC_WRITE, 0, None,
                                    win32file.OPEN_EXISTING, win32file.FILE_ATTRIBUTE_NORMAL, None )

                if hFile == win32file.INVALID_HANDLE_VALUE:
                    hFile = hFile # ¯\_(ツ)_/¯
                
                createTime = pywintypes.Time(file.time.create >> 32)
                lastAccessTime = pywintypes.Time(file.time.lastAccess >> 32)
                lastWriteTime = pywintypes.Time(file.time.lastWrite >> 32)
                
                win32file.SetFileTime( hFile, createTime, lastAccessTime, lastWriteTime )
                
                win32file.CloseHandle(hFile)

                # ファイル属性を付ける
                win32file.SetFileAttributesW(str(self.directory / pName), file.attributes)
                """

            if i == _dir.fileHeadNum - 1:
                break
            else:
                last_index += fileHeadSize
                file = DARC_FILEHEAD(fileP[last_index:])
                if self.only_game_dat:
                    return
        self.directory = old_directory

    def getOriginalFileName(self, fileNameTable) -> Path:
        filename_start_pos = fileNameTable[0] * 4 + 4
        null_pos = fileNameTable[filename_start_pos:].find(0x0)
        pName = fileNameTable[filename_start_pos : filename_start_pos + null_pos]
        try:
            return Path(pName.decode("utf8"))
        except UnicodeDecodeError:
            return Path(pName.decode("cp932"))


def main() -> None:
    decompiler = DXArchive()

    # Ver 6
    archivePath_v6 = Path("./test_wolf/version_220.wolf")
    archivePath_v6 = Path("./test_wolf/version_221.wolf")
    archivePath_v6 = Path("./test_wolf/version_224.wolf")
    key_2_20_2_24 = bytearray(
        [0x38, 0x50, 0x40, 0x28, 0x72, 0x4F, 0x21, 0x70, 0x3B, 0x73, 0x35, 0x38]
    )
    key_2_20_2_24 = bytearray(b"8P@(rO!p;s58")

    # Setup
    archivePath = archivePath_v6
    keyString_ = key_2_20_2_24
    outputPath = Path("output")
    only_game_dat = True

    decompiled = decompiler.decodeArchive(
        archivePath=archivePath,
        outputPath=outputPath,
        only_game_dat=only_game_dat,
        keyString_=keyString_,
    )

    if decompiled:
        print(f"Decompiled {archivePath.name}")
    else:
        print(f"Couldn't decompile {archivePath.name}")


if __name__ == "__main__":
    main()
