from io import SEEK_END, SEEK_SET, TextIOWrapper
from pathlib import Path
from stat import FILE_ATTRIBUTE_DIRECTORY

try:
    from .huffman import huffman_Decode
except ImportError:
    from huffman import huffman_Decode
import struct


DXA_HEAD = struct.unpack("H", b"DX")[0]  # Header
DXA_VER = 0x0008  # Version
DXA_VER_MIN = 0x0008  # The minimum version supported.
DXA_BUFFERSIZE = 0x1000000  # Size of the buffer used when creating the archive
DXA_KEY_BYTES = 7  # Number of bytes in the key
DXA_KEY_STRING_LENGTH = 63  # Length of key string
DXA_KEY_STRING_MAXLENGTH = 2048  # Size of key string buffer

# Default key string
defaultKeyString = bytearray(
    [0x44, 0x58, 0x42, 0x44, 0x58, 0x41, 0x52, 0x43, 0x00]
)  # "DXLIBARC" # It's actually b"DXBDXARC\x00" ¯\_(ツ)_/¯

# Length of the log string
logStringLength = 0

# Flags
DXA_FLAG_NO_KEY = 0x00000001  # No key processing
DXA_FLAG_NO_HEAD_PRESS = 0x00000002  # No header compression


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
    flags = None  # Flags (DXA_FLAG_NO_KEY, etc.)
    huffmanEncodeKB = None  # Size to be compressed by Huffman before and after the file (unit: kilobytes If 0xff, all files are compressed)
    reserve = None  # Reserved area

    def __init__(self, header_bytes=None):
        if header_bytes is None:
            return
        unpacked = struct.unpack("HHIQQQQIIB14sB", header_bytes)
        self.head = unpacked[0]
        self.version = unpacked[1]
        self.headSize = unpacked[2]
        self.dataStartAddress = unpacked[3]
        self.fileNameTableStartAddress = unpacked[4]
        self.fileTableStartAddress = unpacked[5]
        self.directoryTableStartAddress = unpacked[6]
        self.charCodeFormat = unpacked[7]
        self.flags = unpacked[8]
        self.huffmanEncodeKB = unpacked[9]
        self.reserve = unpacked[10]

    def __len__(self) -> int:
        return struct.calcsize("HHIQQQQIIB14sB")

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
Head->flags = {self.flags}
Head->huffmanEncodeKB = {self.huffmanEncodeKB}
Head->reserve = {self.reserve}
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
    huffPressDataSize = None  # Size of the data after Huffman compression ( 0xffffffffffffffff: not compressed ) (added in Ver0x0008)

    def __init__(self, fileHead_bytes=None):
        if fileHead_bytes is None:
            return
        unpacked = struct.unpack("QQQQQQQQQ", fileHead_bytes[: len(self)])
        self.nameAddress = unpacked[0]
        self.attributes = unpacked[1]
        self.time = DARC_FILETIME()
        self.time.create = unpacked[2]
        self.time.lastAccess = unpacked[3]
        self.time.lastWrite = unpacked[4]
        self.dataAddress = unpacked[5]
        self.dataSize = unpacked[6]
        self.pressDataSize = unpacked[7]
        self.huffPressDataSize = unpacked[8]

    def __len__(self) -> int:
        return struct.calcsize("QQQQQQQQQ")

    def __repr__(self) -> str:
        return f"""File->nameAddress = {self.nameAddress}
File->attributes = {self.attributes}
File->time.create = {self.time.create}
File->time.lastAccess = {self.time.lastAccess}
File->time.lastWrite = {self.time.lastWrite}
File->dataAddress = {self.dataAddress}
File->dataSize = {self.dataSize}
File->pressDataSize = {self.pressDataSize}
File->huffPressDataSize = {self.huffPressDataSize}"""


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


class ArchivedFile:
    filePath: Path
    compressed: bool
    huffmanCompressed: bool
    key: bytearray | None
    dataStart: int
    dataSize: int
    pressDataSize: int
    huffPressDataSize: int

    def __str__(self) -> str:
        return f"""ArchivedFile(
\tfilePath: {self.filePath}
\tcompressed: {self.compressed}
\thuffmanCompressed: {self.huffmanCompressed}
\tkey: {self.key}
\tdataStart: {self.dataStart}
\tdataSize: {self.dataSize}
\tpressDataSize: {self.pressDataSize}
\thuffPressDataSize: {self.huffPressDataSize}
)"""


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
        self.archivedFiles = []

    def error(self) -> bool:
        if self.fp is not None:
            self.fp.close()

        return False

    def loadArchive(
        self,
        archivePath: Path,
        outputPath: Path = Path("."),
        keyString_: bytearray = None,
    ):
        self.fp = open(archivePath, mode="rb")
        self.outputPath = outputPath
        self.directory = self.outputPath

        key = bytearray([0] * DXA_KEY_BYTES)
        keyString = bytearray([0] * (DXA_KEY_STRING_LENGTH + 1))

        if keyString_ is None:
            keyString_ = defaultKeyString

        keyStringBytes = len(keyString_)
        if keyStringBytes > DXA_KEY_STRING_LENGTH:
            keyStringBytes = DXA_KEY_STRING_LENGTH

        keyString = keyString_[:keyStringBytes]

        # 鍵の作成
        key = self.keyCreate(keyString, keyStringBytes, key)

        self.archiveHead = DARC_HEAD(self.fp.read(len(DARC_HEAD())))  # 64

        if self.archiveHead.head != DXA_HEAD:
            return self.error()

        if self.archiveHead.version > DXA_VER or self.archiveHead.version < DXA_VER_MIN:
            return self.error()

        headBuffer = [0] * self.archiveHead.headSize

        self.noKey = (self.archiveHead.flags & DXA_FLAG_NO_KEY) != 0

        if self.archiveHead.headSize is None or self.archiveHead.headSize == 0:
            return self.error()

        if (self.archiveHead.flags & DXA_FLAG_NO_HEAD_PRESS) != 0:
            # 圧縮されていない場合は普通に読み込む
            self.fp.seek(self.archiveHead.fileNameTableStartAddress, SEEK_SET)
            headBuffer = self.keyConvFileRead(self.archiveHead.headSize, 0)
        else:
            # 圧縮されたヘッダの容量を取得する
            self.fp.seek(0, SEEK_END)
            fileSize = self.fp.tell()
            self.fp.seek(self.archiveHead.fileNameTableStartAddress, SEEK_SET)
            huffHeadSize = fileSize - self.fp.tell()

            if huffHeadSize is None or huffHeadSize <= 0:
                return self.error()

            huffHeadBuffer = bytearray([0] * huffHeadSize)

            # ハフマン圧縮されたヘッダをメモリに読み込む
            huffHeadBuffer = self.keyConvFileRead(
                huffHeadBuffer, huffHeadSize, None if self.noKey else key, 0
            )

            # ハフマン圧縮されたヘッダの解凍後の容量を取得する
            lzHeadSize = huffman_Decode(huffHeadBuffer, None)

            if lzHeadSize is None or lzHeadSize <= 0:
                return self.error()

            lzHeadBuffer = bytearray([0] * lzHeadSize)

            # ハフマン圧縮されたヘッダを解凍する
            (lzHeadBuffer, originalSize) = huffman_Decode(huffHeadBuffer, lzHeadBuffer)

            # LZ圧縮されたヘッダを解凍する
            (headBuffer, size) = self.decode(lzHeadBuffer, bytearray(headBuffer))

            self.nameTable = headBuffer[: self.archiveHead.fileTableStartAddress]
            self.fileTable = headBuffer[
                self.archiveHead.fileTableStartAddress : self.archiveHead.directoryTableStartAddress
            ]
            self.directoryTable = headBuffer[
                self.archiveHead.directoryTableStartAddress :
            ]

            self.directoryDecode(
                DARC_DIRECTORY(self.directoryTable), key, keyString, keyStringBytes
            )

            return True

    def keyCreate(self, source: bytearray, sourceBytes: int, key: bytearray):
        workBuffer = bytearray([0] * 1024)

        if sourceBytes == 0:
            sourceBytes = len(source)

        # If it's too short, add defaultKeyString
        if sourceBytes < 4:
            sourceTempBuffer = source
            sourceTempBuffer += defaultKeyString
            source = sourceTempBuffer
            sourceBytes = len(source)

        if sourceBytes > len(workBuffer):
            useWorkBuffer = bytearray([0] * sourceBytes)
        else:
            useWorkBuffer = workBuffer

        j = 0
        for i in range(0, sourceBytes, 2):
            useWorkBuffer[j] = source[i]
            j += 1

        CRC32_0 = self.CRC32(useWorkBuffer, j)

        j = 0
        for i in range(1, sourceBytes, 2):
            useWorkBuffer[j] = source[i]
            j += 1

        CRC32_1 = self.CRC32(useWorkBuffer, j)

        key[0] = (CRC32_0 >> 0) % 256
        key[1] = (CRC32_0 >> 8) % 256
        key[2] = (CRC32_0 >> 16) % 256
        key[3] = (CRC32_0 >> 24) % 256
        key[4] = (CRC32_1 >> 0) % 256
        key[5] = (CRC32_1 >> 8) % 256
        key[6] = (CRC32_1 >> 16) % 256

        return key

    def CRC32(self, SrcData: bytearray, SrcDataSize: bytearray) -> int:
        CRC32TableInit = 0
        CRC32Table = []
        CRC = 0xFFFFFFFF

        # テーブルが初期化されていなかったら初期化する
        if CRC32TableInit == 0:
            Magic = 0xEDB88320  # 0x4c11db7 をビットレベルで順番を逆にしたものが 0xedb88320

            for i in range(256):
                Data = i
                for j in range(8):
                    b = Data & 1
                    Data = Data >> 1
                    if b != 0:
                        Data = Data ^ Magic

                CRC32Table.append(Data)

            # テーブルを初期化したフラグを立てる
            CRC32TableInit = 1

        for i in range(SrcDataSize):
            tmp = (CRC ^ SrcData[i]) % 256
            CRC = CRC32Table[tmp] ^ (CRC >> 8)

        return CRC ^ 0xFFFFFFFF

    def keyConvFileRead(
        self, data: bytearray, size: int, key: bytearray, position: int
    ) -> bytearray:
        pos = 0

        if key is not None:
            # ファイルの位置を取得しておく
            if position == -1:
                pos = self.fp.tell()
            else:
                pos = position

        # 読み込む
        data = bytearray(
            self.fp.read(size)
        )  # For assignment in keyConv data[i] ^= key[j]

        if key is not None:
            # データを鍵文字列を使って Xor 演算
            data = self.keyConv(data, size, pos, key)

        return data

    def keyConv(
        self, data: bytearray, size: int, position: int, key: bytearray
    ) -> bytes:
        if key is None:
            return data

        position %= DXA_KEY_BYTES

        if size < 0x100000000:
            j = position % 0xFFFFFFFF
            for i in range(size):
                data[i] ^= key[j]
                j += 1
                if j == DXA_KEY_BYTES:
                    j = 0
        else:
            j = position
            for i in range(size):
                data[i] ^= key[j]
                j += 1
                if j == DXA_KEY_BYTES:
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

        tda = bytearray([0] * destsize)
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
        self,
        directoryInfo: DARC_DIRECTORY,
        key: bytearray,
        keyString: str,
        keyStringBytes: int,
    ) -> None:
        """
        Recursively get all directory information from directoryTable:
            Directory Name
            Information about files inside directory (actual files and other directories)
        """

        # Save current directory
        old_directory = self.directory

        if (
            directoryInfo.directoryAddress != 0xFFFFFFFFFFFFFFFF
            and directoryInfo.parentDirectoryAddress != 0xFFFFFFFFFFFFFFFF
        ):
            dirFile = DARC_FILEHEAD(self.fileTable[directoryInfo.directoryAddress :])
            pName = self.getOriginalFileName(self.nameTable[dirFile.nameAddress :])
            self.directory = self.directory / pName

        # Get info about file sinside this directory
        for i in range(directoryInfo.fileHeadNum):
            offset = len(DARC_FILEHEAD()) * i
            fileInfo = DARC_FILEHEAD(
                self.fileTable[directoryInfo.fileHeadAddress + offset :]
            )

            # Is the file another directory?
            if fileInfo.attributes & FILE_ATTRIBUTE_DIRECTORY:
                # Get that info too
                self.directoryDecode(
                    DARC_DIRECTORY(self.directoryTable[fileInfo.dataAddress :]),
                    key,
                    keyString,
                    keyStringBytes,
                )
            else:
                # It's an actual file
                pName = self.getOriginalFileName(self.nameTable[fileInfo.nameAddress :])
                filePath = self.directory / pName

                archivedFile = ArchivedFile()
                archivedFile.filePath = filePath
                archivedFile.compressed = fileInfo.pressDataSize != 0xFFFFFFFFFFFFFFFF
                archivedFile.huffmanCompressed = (
                    fileInfo.huffPressDataSize != 0xFFFFFFFFFFFFFFFF
                )
                archivedFile.key = None
                archivedFile.dataStart = (
                    self.archiveHead.dataStartAddress + fileInfo.dataAddress
                )
                archivedFile.dataSize = fileInfo.dataSize
                archivedFile.pressDataSize = fileInfo.pressDataSize
                archivedFile.huffPressDataSize = fileInfo.huffPressDataSize

                # ファイル個別の鍵を作成
                if not self.noKey:
                    keyStringBuffer = self.createKeyFileString(
                        keyString, keyStringBytes, directoryInfo, fileInfo
                    )
                    keyStringBufferBytes = len(keyStringBuffer)
                    lKey = self.keyCreate(
                        keyStringBuffer,
                        keyStringBufferBytes,
                        bytearray([0] * DXA_KEY_BYTES),
                    )
                    archivedFile.key = lKey

                self.archivedFiles.append(archivedFile)

            if i == directoryInfo.fileHeadNum - 1:
                break

        # Like going one directory up ../
        self.directory = old_directory

    def getOriginalFileName(self, fileNameTable) -> Path:
        filename_start_pos = fileNameTable[0] * 4 + 4
        null_pos = fileNameTable[filename_start_pos:].find(0x0)
        pName = fileNameTable[filename_start_pos : filename_start_pos + null_pos]
        try:
            return Path(pName.decode("utf8"))
        except UnicodeDecodeError:
            return Path(pName.decode("cp932"))  # For Japanese characters

    def createKeyFileString(
        self,
        keyString,
        keyStringBytes,
        directory: DARC_DIRECTORY,
        fileHead: DARC_FILEHEAD,
    ) -> bytearray:
        # At the end of the day this create a key that is comprised of
        # keyString + FILENAME + PARENT DIRECTORY [ + PARENT PARENT DIRECTORY ]
        # So the key for ./test1/test2/test3/file.txt
        # would be keyStringFILE.TXTTEST3TEST2TEST1
        fileString = bytearray([0] * DXA_KEY_STRING_MAXLENGTH)
        # 最初にパスワードの文字列をセット
        if keyString is not None and keyStringBytes != 0:
            fileString[:keyStringBytes] = keyString[:keyStringBytes]
            fileString[keyStringBytes] = 0
            startAddr = keyStringBytes
        else:
            fileString[0] = 0
            startAddr = 0

        og_startAddr = startAddr

        fileString[DXA_KEY_STRING_MAXLENGTH - 8 : DXA_KEY_STRING_MAXLENGTH] = bytearray(
            b"00000000"
        )

        src = self.nameTable[fileHead.nameAddress + 4 :]
        amount = (DXA_KEY_STRING_MAXLENGTH - 8) - og_startAddr
        end_string = min(src.find(0x0), amount - 1)
        copied = src[:end_string]
        fileString[startAddr : startAddr + len(copied)] = copied
        startAddr = startAddr + len(copied)

        if directory.parentDirectoryAddress != 0xFFFFFFFFFFFFFFFF:
            while True:
                fileHead = DARC_FILEHEAD(self.fileTable[directory.directoryAddress :])
                src = self.nameTable[fileHead.nameAddress + 4 :]
                amount = (DXA_KEY_STRING_MAXLENGTH - 8) - og_startAddr
                end_string = min(src.find(0x0), amount - 1)
                copied = src[:end_string]
                fileString[startAddr : startAddr + len(copied)] = copied
                startAddr = startAddr + len(copied)
                directory = DARC_DIRECTORY(
                    self.directoryTable[directory.parentDirectoryAddress :]
                )
                if directory.parentDirectoryAddress == 0xFFFFFFFFFFFFFFFF:
                    break

        new_key = fileString[:startAddr]
        return new_key

    def extractAll(self) -> None:
        for archivedFile in self.archivedFiles:
            self.extractFile(archivedFile)

    def extractFile(self, archivedFile: ArchivedFile) -> None:
        if not archivedFile.filePath.parent.exists():
            archivedFile.filePath.parent.mkdir(parents=True)

        destP = open(archivedFile.filePath, mode="wb")

        if archivedFile.dataSize != 0:
            outputSize = archivedFile.dataSize

            if self.fp.tell() != archivedFile.dataStart:
                self.fp.seek(archivedFile.dataStart, SEEK_SET)

            if archivedFile.compressed:
                outputSize += archivedFile.pressDataSize

            if archivedFile.huffmanCompressed:
                outputSize += archivedFile.huffPressDataSize

            output = bytearray([0] * (outputSize))

            # If there's huffman compression
            if archivedFile.huffmanCompressed:
                keyConvFileReadSize = (
                    archivedFile.pressDataSize
                    if archivedFile.compressed
                    else archivedFile.dataSize
                )

                read = self.keyConvFileRead(
                    output,
                    archivedFile.huffPressDataSize,
                    archivedFile.key,
                    archivedFile.dataSize,
                )
                output[: len(read)] = read

                (decoded, _) = huffman_Decode(
                    output, output[archivedFile.huffPressDataSize :]
                )
                output[archivedFile.huffPressDataSize :] = decoded

                if (
                    self.archiveHead.huffmanEncodeKB != 0xFF
                    and keyConvFileReadSize
                    > self.archiveHead.huffmanEncodeKB * 1024 * 2
                ):
                    amount_to_move = self.archiveHead.huffmanEncodeKB * 1024
                    start_dest = (
                        archivedFile.huffPressDataSize
                        + keyConvFileReadSize
                        - self.archiveHead.huffmanEncodeKB * 1024
                    )
                    start_src = (
                        archivedFile.huffPressDataSize
                        + self.archiveHead.huffmanEncodeKB * 1024
                    )
                    moved_bytes = output[start_src : start_src + amount_to_move]
                    output[start_dest : start_dest + amount_to_move] = moved_bytes

                    data = self.keyConvFileRead(
                        output[
                            archivedFile.huffPressDataSize
                            + self.archiveHead.huffmanEncodeKB * 1024 :
                        ],
                        keyConvFileReadSize
                        - self.archiveHead.huffmanEncodeKB * 1024 * 2,
                        archivedFile.key,
                        archivedFile.dataSize + archivedFile.huffPressDataSize,
                    )
                    output[
                        archivedFile.huffPressDataSize
                        + self.archiveHead.huffmanEncodeKB * 1024 : len(data)
                    ] = data

                if archivedFile.compressed:
                    (decoded, _) = self.decode(
                        output[archivedFile.huffPressDataSize :],
                        output[
                            archivedFile.huffPressDataSize
                            + archivedFile.pressDataSize :
                        ],
                    )

                    output[
                        archivedFile.huffPressDataSize + archivedFile.pressDataSize :
                    ] = decoded
                    destP.write(
                        output[
                            archivedFile.huffPressDataSize
                            + archivedFile.pressDataSize : archivedFile.huffPressDataSize
                            + archivedFile.pressDataSize
                            + archivedFile.dataSize
                        ]
                    )
                else:
                    destP.write(
                        output[
                            archivedFile.huffPressDataSize : archivedFile.huffPressDataSize
                            + archivedFile.dataSize
                        ]
                    )

            else:
                # There's no huffman compression, check for regular compression
                if archivedFile.compressed:
                    read = self.keyConvFileRead(
                        output,
                        archivedFile.pressDataSize,
                        archivedFile.key,
                        archivedFile.dataSize,
                    )
                    output[: len(read)] = read

                    (decoded, _) = self.decode(
                        output, output[archivedFile.pressDataSize :]
                    )
                    output[archivedFile.pressDataSize :] = decoded

                    destP.write(
                        output[
                            archivedFile.pressDataSize : archivedFile.pressDataSize
                            + archivedFile.dataSize
                        ]
                    )
                else:
                    writeSize = 0
                    while writeSize < archivedFile.dataSize:
                        if archivedFile.dataSize - writeSize > DXA_BUFFERSIZE:
                            moveSize = DXA_BUFFERSIZE
                        else:
                            moveSize = archivedFile.dataSize - writeSize

                        read = self.keyConvFileRead(
                            output,
                            moveSize,
                            archivedFile.key,
                            archivedFile.dataSize + writeSize,
                        )
                        output[: len(read)] = read

                        destP.write(output[:moveSize])

                        writeSize += moveSize

        destP.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if not self.fp.closed:
            self.fp.close()


def main() -> None:
    # DXArchive V8
    archivePath_v8 = Path("./test_wolf/version_2255.wolf")
    archivePath_v8 = Path("./test_wolf/version_2264.wolf")
    archivePath_v8 = Path("./test_wolf/version_2271.wolf")
    archivePath_v8 = Path("./test_wolf/version_2281.wolf")
    key_2_25_2_81 = bytearray(
        [
            57,
            0x4C,
            0x46,
            0x52,
            0x50,
            0x72,
            0x4F,
            0x21,
            0x70,
            0x28,
            0x3B,
            0x73,
            0x35,
            0x28,
            0x28,
            0x38,
            0x50,
            0x40,
            0x28,
            0x28,
            0x55,
            0x46,
            0x57,
            0x6C,
            0x75,
            0x24,
            0x23,
            0x35,
            0x28,
            0x3D,
        ]
    )
    key_2_25_2_81 = bytearray(b"WLFRPrO!p(;s5((8P@((UFWlu$#5(=")

    # Setup
    archivePath = archivePath_v8
    keyString_ = key_2_25_2_81
    outputPath = Path("output")

    with DXArchive() as decompiler:
        if decompiler.loadArchive(
            archivePath=archivePath, outputPath=outputPath, keyString_=keyString_
        ):
            for archivedFile in decompiler.archivedFiles:
                if (
                    archivedFile.filePath.name == "Game.dat"
                    or archivedFile.filePath.suffix in [".png", ".jpg", ".ogg", ".mp3"]
                ):
                    decompiler.extractFile(archivedFile)


if __name__ == "__main__":
    main()
