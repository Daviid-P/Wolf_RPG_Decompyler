from io import SEEK_END, SEEK_SET, TextIOWrapper
from pathlib import Path
from stat import FILE_ATTRIBUTE_DIRECTORY
try:
    from .huffman import huffman_Decode
except ImportError:
    from huffman import huffman_Decode
import struct


DXA_HEAD = struct.unpack("H",b"DX")[0]     # Header
DXA_VER = 0x0008                        # Version
DXA_VER_MIN = 0x0008                    # The minimum version supported.
DXA_BUFFERSIZE = 0x1000000              # Size of the buffer used when creating the archive
DXA_KEY_BYTES = 7                       # Number of bytes in the key
DXA_KEY_STRING_LENGTH = 63              # Length of key string
DXA_KEY_STRING_MAXLENGTH = 2048         # Size of key string buffer

# Default key string
defaultKeyString = bytearray([0x44, 0x58, 0x42, 0x44, 0x58, 0x41, 0x52, 0x43, 0x00]) # "DXLIBARC" # It's actually b"DXBDXARC\x00" ¯\_(ツ)_/¯

# Length of the log string
logStringLength = 0

# Flags
DXA_FLAG_NO_KEY = 0x00000001            # No key processing
DXA_FLAG_NO_HEAD_PRESS = 0x00000002     # No header compression

class DARC_HEAD():
    head = None                            # Header
    version = None                         # Version
    headSize = None                        # Total size of the file without the DARC_HEAD header information.
    dataStartAddress = None                # The data address where the data of the first file is stored (the first address of the file is assumed to be address 0)
    fileNameTableStartAddress = None       # The first address of the file name table (the first address of the file is assumed to be address 0)
    fileTableStartAddress = None           # First address of the file table (assumes the address of the member variable FileNameTableStartAddress to be 0)
    directoryTableStartAddress = None      # First address of the directory table (assumes the address of the member variable FileNameTableStartAddress to be 0)
                                           # The DARC_DIRECTORY structure located at address 0 is the root directory.
    charCodeFormat = None                  # Code page number used for the file name
    flags = None                           # Flags (DXA_FLAG_NO_KEY, etc.)
    huffmanEncodeKB = None                 # Size to be compressed by Huffman before and after the file (unit: kilobytes If 0xff, all files are compressed)
    reserve = None                         # Reserved area

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
class DARC_FILETIME():
    create = None            # Creation time
    lastAccess = None        # Last access time
    lastWrite = None         # Last update time
    
    def __init__(self, fileTime_bytes=None):
        if fileTime_bytes is None:
            return
        unpacked = struct.unpack("QQQ", fileTime_bytes[:len(self)])
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
class DARC_FILEHEAD():
    nameAddress = None           # Address where the file name is stored (the address of the member variable FileNameTableStartAddress of the ARCHIVE_HEAD structure is set to address 0)
    attributes = None            # File attributes
    time = None                  # Time information
    dataAddress = None           # Address where the file is stored.
                          #            In the case of a file, the address indicated by the member variable DataStartAddress of the DARC_HEAD structure shall be address 0.
                          #            In the case of a directory: The address indicated by the member variable "DirectoryTableStartAddress" of the DARC_HEAD structure shall be set to address 0.
    dataSize = None              # Data size of the file
    pressDataSize = None         # The size of the data after compression ( 0xffffffffffffffffff: not compressed ) (added in Ver0x0002)
    huffPressDataSize = None     # Size of the data after Huffman compression ( 0xffffffffffffffff: not compressed ) (added in Ver0x0008)
    
    def __init__(self, fileHead_bytes=None):
        if fileHead_bytes is None:
            return
        unpacked =  struct.unpack("QQQQQQQQQ", fileHead_bytes[:len(self)])
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
class DARC_DIRECTORY():
    directoryAddress = None           # Address where my DARC_FILEHEAD is stored (Address 0 is the address indicated by the member variable FileTableStartAddress of the DARC_HEAD structure)
    parentDirectoryAddress = None     # The address where DARC_DIRECTORY of the parent directory is stored ( The address indicated by the member variable DirectoryTableStartAddress of the DARC_HEAD structure is set to address 0.)
    fileHeadNum = None                # Number of files in the directory
    fileHeadAddress = None            # The address where the header column of the file in the directory is stored ( The address indicated by the member variable FileTableStartAddress of the DARC_HEAD structure is set to address 0.)
    
    def __init__(self, directory_bytes=None):
        if directory_bytes is None:
            return
        unpacked = struct.unpack("QQQQ", directory_bytes[:len(self)])
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
class DARC_ENCODEINFO():
    totalFileNum = None              # Total number of files
    compFileNum = None               # Number of files processed.
    prevDispTime = None              # Time of the last status output
    processFileName = None           # Name of the file currently being processed
    outputStatus = None              # Whether status output is performed or not

    def __repr__(self) -> str:
        return f"""
self.totalFileNum = {self.totalFileNum}
self.compFileNum = {self.compFileNum}
self.prevDispTime = {self.prevDispTime}
self.processFileName = {self.processFileName}
self.outputStatus = {self.outputStatus}
"""

class DXArchive():
    MIN_COMPRESS = 4                        # Minimum number of compressed bytes
    MAX_SEARCHLISTNUM = 64                  # Maximum number of lists to traverse to find the maximum match length
    MAX_SUBLISTNUM = 65536                  # Maximum number of sublists to reduce compression time
    MAX_COPYSIZE = 0x1fff + MIN_COMPRESS    # Maximum size to copy from a reference address ( Maximum copy size that a compression code can represent + Minimum number of compressed bytes )
    MAX_ADDRESSLISTNUM = 1024 * 1024 * 1    # Maximum size of slide dictionary
    MAX_POSITION = 1 << 24                  # Maximum relative address that can be referenced ( 16MB )

    def __init__(self) -> None:
        pass

    def error(self) -> bool:
        if self.fp is not None:
            self.fp.close()

        return False

    def decodeArchive(self, archivePath: Path, outputPath: Path = Path('.'), only_game_dat: bool = False, keyString_: bytearray = None ):
        self.fp = open( archivePath, mode="rb" )
        self.outputPath = outputPath
        self.directory = self.outputPath
        self.only_game_dat = only_game_dat
        
        key = bytearray([0] * DXA_KEY_BYTES)
        keyString = bytearray([0] * (DXA_KEY_STRING_LENGTH + 1))
        keyStringBuffer = bytearray([0] * DXA_KEY_STRING_MAXLENGTH)
        
        if keyString_ is None:
            keyString_ = defaultKeyString
        
        keyStringBytes = len(keyString_)
        if keyStringBytes > DXA_KEY_STRING_LENGTH:
            keyStringBytes = DXA_KEY_STRING_LENGTH
        
        keyString = keyString_[:keyStringBytes]

        # 鍵の作成
        key = self.keyCreate( keyString, keyStringBytes, key )

        head = DARC_HEAD(self.fp.read(len(DARC_HEAD()))) # 64

        if head.head != DXA_HEAD:
            return self.error()

        if head.version > DXA_VER or head.version < DXA_VER_MIN:
            return self.error()

        headBuffer = [0] * head.headSize
        

        noKey = ( head.flags & DXA_FLAG_NO_KEY ) != 0

        if head.headSize is None or head.headSize == 0:
            return self.error()

        if ( head.flags & DXA_FLAG_NO_HEAD_PRESS ) != 0:
            # 圧縮されていない場合は普通に読み込む
            self.fp.seek(head.fileNameTableStartAddress, SEEK_SET)
            headBuffer = self.keyConvFileRead( head.headSize, 0 )
        else:
            # 圧縮されたヘッダの容量を取得する
            self.fp.seek(0, SEEK_END)
            fileSize = self.fp.tell()
            self.fp.seek(head.fileNameTableStartAddress, SEEK_SET)
            huffHeadSize =  fileSize - self.fp.tell()

            if huffHeadSize is None or huffHeadSize <= 0:
                return self.error()

            huffHeadBuffer = bytearray([0] * huffHeadSize)

            # ハフマン圧縮されたヘッダをメモリに読み込む
            huffHeadBuffer = self.keyConvFileRead(huffHeadBuffer, huffHeadSize, self.fp, None if noKey else key, 0 )

            # ハフマン圧縮されたヘッダの解凍後の容量を取得する
            lzHeadSize = huffman_Decode( huffHeadBuffer, None )

            if lzHeadSize is None or lzHeadSize <= 0:
                return self.error()
            
            lzHeadBuffer = bytearray([0] * lzHeadSize)

            # ハフマン圧縮されたヘッダを解凍する
            (lzHeadBuffer, originalSize) = huffman_Decode( huffHeadBuffer, lzHeadBuffer)

            # LZ圧縮されたヘッダを解凍する
            (headBuffer, size) = self.decode( lzHeadBuffer, bytearray(headBuffer) )
            
            nameP = headBuffer
            fileP = nameP[head.fileTableStartAddress:]
            dirP  = nameP[head.directoryTableStartAddress:]
            self.directoryDecode(nameP, dirP, fileP, head, DARC_DIRECTORY(dirP), self.fp, key, keyString, keyStringBytes, noKey, keyStringBuffer)
            self.fp.close()
            return True
    
    def keyCreate(self, source: bytearray, sourceBytes: int, key: bytearray ):
        workBuffer = bytearray([0] * 1024)

        if sourceBytes == 0 :
            sourceBytes = len( source )

        # If it's too short, add defaultKeyString
        if sourceBytes < 4:
            sourceTempBuffer = source
            sourceTempBuffer += defaultKeyString
            source = sourceTempBuffer
            sourceBytes = len(source)

        if sourceBytes > len( workBuffer ):
            useWorkBuffer = bytearray([0] * sourceBytes)
        else:
            useWorkBuffer = workBuffer

        j = 0
        for i in range(0, sourceBytes, 2):
            useWorkBuffer[j] = source[i]
            j += 1

        CRC32_0 = self.CRC32( useWorkBuffer, j )

        j = 0
        for i in range(1, sourceBytes, 2):
            useWorkBuffer[j] = source[i]
            j += 1

        CRC32_1 = self.CRC32( useWorkBuffer, j )

        key[0] = (CRC32_0 >>  0)%256
        key[1] = (CRC32_0 >>  8)%256
        key[2] = (CRC32_0 >> 16)%256
        key[3] = (CRC32_0 >> 24)%256
        key[4] = (CRC32_1 >>  0)%256
        key[5] = (CRC32_1 >>  8)%256
        key[6] = (CRC32_1 >> 16)%256
        
        return key

    def CRC32(self, SrcData, SrcDataSize) -> int:
        CRC32TableInit = 0
        CRC32Table = []
        CRC = 0xffffffff


        # テーブルが初期化されていなかったら初期化する
        if CRC32TableInit == 0:
            Magic = 0xedb88320    # 0x4c11db7 をビットレベルで順番を逆にしたものが 0xedb88320

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
            tmp = (CRC ^ SrcData[ i ]) % 256
            CRC = CRC32Table[ tmp ] ^ ( CRC >> 8 )

        return CRC ^ 0xffffffff ;

    def keyConvFileRead(self, data, size, fp, key, position ) -> bytearray:
        pos = 0

        if key is not None:
            # ファイルの位置を取得しておく
            if position == -1:
                pos = fp.tell()
            else:
                pos = position


        # 読み込む
        data = bytearray(fp.read(size)) # For assignment in keyConv data[i] ^= key[j]

        if key is not None:
            # データを鍵文字列を使って Xor 演算
            data = self.keyConv( data, size, pos, key)

        return data

    def keyConv(self, data, size, position, key) -> bytes:
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
        srcp  = src

        destsize = struct.unpack("I", srcp[0:4])[0]
        srcsize = struct.unpack("I", srcp[4:8])[0] - 9

        keycode = srcp[8]

        if dest is None:
            return destsize
        
        sp  = srcp[9:]

        tda = bytearray([0] * destsize)
        tdac = 0

        while srcsize > 0:
            if sp[0] != keycode:
                tda[tdac] = sp[0]
                tdac +=1
                sp = sp[1:]
                srcsize -= 1
                continue

            if sp[1] == keycode:
                tda[tdac] = keycode%256
                tdac +=1
                sp = sp[2:]
                srcsize -= 2
                continue

            code = sp[1]

            if code > keycode:
                code -= 1

            sp = sp[2:]
            srcsize -= 2


            conbo = code >> 3
            if code & ( 0x1 << 2 ):
                conbo |= sp[0] << 5
                sp = sp[1:]
                srcsize -=1

            conbo += self.MIN_COMPRESS

            indexsize = code & 0x3
            if indexsize == 0:
                index = sp[0]
                sp = sp[1:]
                srcsize -= 1
            elif indexsize == 1:
                index = struct.unpack('H', sp[0:2])[0]
                sp = sp[2:]
                srcsize -= 2 ;
            elif indexsize == 2:
                index = struct.unpack('H', sp[0:2])[0] | (sp[2] << 16 )
                sp = sp[3:]
                srcsize -= 3

            index += 1

            if index < conbo:
                num  = index
                while conbo > num:
                    copied_bytes = tda[tdac-num:tdac-num+num]
                    tda[tdac:tdac+num] = copied_bytes
                    tdac += num
                    conbo -= num
                    num   += num
                if conbo != 0:
                    copied_bytes = tda[tdac-num:tdac-num+conbo]
                    tda[tdac:tdac+conbo] = copied_bytes
                    tdac += conbo
            else:
                copied_bytes = tda[tdac-index:tdac-index+conbo]
                tda[tdac:tdac+conbo] = copied_bytes
                tdac += conbo

        return (tda, destsize)

    def directoryDecode(self, nameP, dirP, fileP, head: DARC_HEAD, _dir: DARC_DIRECTORY, arcP, key, keyString, keyStringBytes, noKey, keyStringBuffer) -> None:
        old_directory = self.directory
        
        if _dir.directoryAddress != 0xffffffffffffffff and _dir.parentDirectoryAddress != 0xffffffffffffffff:
            dirFile = DARC_FILEHEAD(fileP[_dir.directoryAddress:])
            pName = self.getOriginalFileName(nameP[dirFile.nameAddress:])
            self.directory = self.directory / pName
            self.directory.mkdir(parents=True, exist_ok=True)
        
        lKey = bytearray([0] * DXA_KEY_BYTES)
        fileHeadSize = len( DARC_FILEHEAD() )
        file = DARC_FILEHEAD(fileP[_dir.fileHeadAddress:])
        last_index = _dir.fileHeadAddress
        for i in range(_dir.fileHeadNum):
            if file.attributes & FILE_ATTRIBUTE_DIRECTORY:
                # ディレクトリの場合は再帰をかける
                self.directoryDecode( nameP, dirP, fileP, head, DARC_DIRECTORY(dirP[file.dataAddress:]), arcP, key, keyString, keyStringBytes, noKey, keyStringBuffer )
                if self.only_game_dat:
                    if "BasicData" not in str(self.directory):
                        last_index += fileHeadSize
                        file = DARC_FILEHEAD(fileP[last_index:])
                        continue
            else:
                # ファイルの場合は展開する
                
                # バッファを確保する
                buffer = bytearray([0] * DXA_BUFFERSIZE)
                if buffer is None or len(buffer) == 0:
                    return -1

                # ファイルを開く
                pName = self.getOriginalFileName(nameP[file.nameAddress:])
                if self.only_game_dat:
                    if str(pName) != "Game.dat":
                        last_index += fileHeadSize
                        file = DARC_FILEHEAD(fileP[last_index:])
                        continue
                if not self.directory.exists():
                    self.directory.mkdir(parents=True)
                destP = open(self.directory / pName, mode="wb")
                
                # ファイル個別の鍵を作成
                if not noKey:
                    keyStringBuffer = self.createKeyFileString( int(head.charCodeFormat), keyString, keyStringBytes, _dir, file, fileP, dirP, nameP, keyStringBuffer )
                    keyStringBufferBytes = len(keyStringBuffer)
                    
                    lKey = self.keyCreate( keyStringBuffer, keyStringBufferBytes, lKey )
                
                # データがある場合のみ転送
                if file.dataSize != 0:
                    # 初期位置をセットする
                    if arcP.tell() != head.dataStartAddress + file.dataAddress:
                        arcP.seek(head.dataStartAddress + file.dataAddress, SEEK_SET)
                        
                    # データが圧縮されているかどうかで処理を分岐
                    if file.pressDataSize != 0xffffffffffffffff:
                        # 圧縮されている場合
                        # ハフマン圧縮もされているかどうかで処理を分岐
                        if file.huffPressDataSize != 0xffffffffffffffff:
                            # 圧縮データが収まるメモリ領域の確保
                            temp = bytearray([0] * (file.pressDataSize + file.huffPressDataSize + file.dataSize))
                            
                            # 圧縮データの読み込み
                            read = self.keyConvFileRead( temp, file.huffPressDataSize, arcP, None if noKey else lKey, file.dataSize )
                            temp[:len(read)] = read
                            
                            # ハフマン圧縮を解凍
                            (decoded, _) = huffman_Decode( temp, temp[file.huffPressDataSize:])
                            temp[file.huffPressDataSize:] = decoded

                            # ファイルの前後をハフマン圧縮している場合は処理を分岐
                            if head.huffmanEncodeKB != 0xff and file.pressDataSize > head.huffmanEncodeKB * 1024 * 2:
                                # 解凍したデータの内、後ろ半分を移動する
                                amount_to_move = head.huffmanEncodeKB * 1024
                                start_dest = file.huffPressDataSize + file.pressDataSize - head.huffmanEncodeKB * 1024
                                start_src = file.huffPressDataSize + head.huffmanEncodeKB * 1024
                                moved_bytes = temp[start_src:start_src+amount_to_move]
                                temp[start_dest:start_dest+amount_to_move] = moved_bytes

                                # 残りのLZ圧縮データを読み込む
                                data = self.keyConvFileRead(temp[file.huffPressDataSize + head.huffmanEncodeKB * 1024:],
                                    file.pressDataSize - head.huffmanEncodeKB * 1024 * 2,
                                    arcP, None if noKey else lKey, file.dataSize + file.huffPressDataSize )
                                temp[file.huffPressDataSize + head.huffmanEncodeKB * 1024:len(data)] = data
                        
                            # 解凍
                            
                            (decoded, _) = self.decode(temp[file.huffPressDataSize:], temp[file.huffPressDataSize + file.pressDataSize:])
                            temp[file.huffPressDataSize+file.pressDataSize:] = decoded
                        
                            # 書き出し
                            destP.write(temp[file.huffPressDataSize + file.pressDataSize:file.huffPressDataSize + file.pressDataSize + file.dataSize])
                        
                        else:
                            # 圧縮データが収まるメモリ領域の確保
                            temp = bytearray([0] * (file.pressDataSize + file.dataSize))

                            # 圧縮データの読み込み
                            read = self.keyConvFileRead( temp, file.PressDataSize, arcP, None if noKey else lKey, file.dataSize )
                            temp[:len(read)] = read
                        
                            # 解凍
                            (decoded, _) = self.decode(temp, temp[file.pressDataSize:])
                            temp[file.pressDataSize:] = decoded
                        
                            # 書き出し
                            destP.write(temp[file.pressDataSize:file.pressDataSize + file.dataSize])
                    else:
                        # 圧縮されていない場合
                    
                        # ハフマン圧縮はされているかどうかで処理を分岐
                        if file.huffPressDataSize != 0xffffffffffffffff:
                            
                            # 圧縮データが収まるメモリ領域の確保
                            temp = bytearray([0] * (file.huffPressDataSize + file.dataSize))
                            
                            # 圧縮データの読み込み
                            read = self.keyConvFileRead( temp, file.huffPressDataSize, arcP, None if noKey else lKey, file.dataSize )
                            temp[:len(read)] = read
                            
                            # ハフマン圧縮を解凍
                            (decoded, _) = huffman_Decode( temp, temp[file.huffPressDataSize:])
                            temp[file.huffPressDataSize:] = decoded

                            # ファイルの前後をハフマン圧縮している場合は処理を分岐
                            if head.huffmanEncodeKB != 0xff and file.dataSize > head.huffmanEncodeKB * 1024 * 2:
                                # 解凍したデータの内、後ろ半分を移動する
                                amount_to_move = head.huffmanEncodeKB * 1024
                                start_dest = file.huffPressDataSize + file.dataSize - head.huffmanEncodeKB * 1024
                                start_src = file.huffPressDataSize + head.huffmanEncodeKB * 1024
                                moved_bytes = temp[start_src:start_src+amount_to_move]
                                temp[start_dest:start_dest+amount_to_move] = moved_bytes

                                # 残りのLZ圧縮データを読み込む
                                data = self.keyConvFileRead(temp[file.huffPressDataSize + head.huffmanEncodeKB * 1024:],
                                    file.dataSize - head.huffmanEncodeKB * 1024 * 2,
                                    arcP, None if noKey else lKey, file.dataSize + file.huffPressDataSize )
                                temp[file.huffPressDataSize + head.huffmanEncodeKB * 1024:] = data
                            
                            # 書き出し
                            destP.write(temp[file.huffPressDataSize:file.huffPressDataSize + file.dataSize])
                        else:
                            # 転送処理開始
                            writeSize = 0
                            while writeSize < file.dataSize:
                                if file.dataSize - writeSize > DXA_BUFFERSIZE:
                                    moveSize = DXA_BUFFERSIZE
                                else:
                                    moveSize = file.dataSize - writeSize

                                # ファイルの反転読み込み
                                read = self.keyConvFileRead( buffer, moveSize, arcP, None if noKey else lKey, file.dataSize + writeSize )
                                buffer[:len(read)] = read

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
            
            if i == _dir.fileHeadNum-1:
                break
            else:
                last_index += fileHeadSize
                file = DARC_FILEHEAD(fileP[last_index:])
                if self.only_game_dat:
                    return
        # Like going one directory up ../
        self.directory = old_directory 
    
    def getOriginalFileName(self, fileNameTable) -> Path:
        filename_start_pos = fileNameTable[0] * 4 + 4
        null_pos = fileNameTable[filename_start_pos:].find(0x0)
        pName = fileNameTable[filename_start_pos:filename_start_pos+null_pos]
        try:
            return Path(pName.decode("utf8"))
        except UnicodeDecodeError:
            return Path(pName.decode("cp932")) # For Japanese characters
        
    def createKeyFileString(self, charCodeFormat, keyString, keyStringBytes, directory: DARC_DIRECTORY, fileHead: DARC_FILEHEAD, fileTable, directoryTable, nameTable, fileString) -> bytearray:
        # 最初にパスワードの文字列をセット
        if keyString is not None and keyStringBytes != 0:
            fileString[:keyStringBytes] = keyString[:keyStringBytes]
            fileString[ keyStringBytes ] = 0
            startAddr = keyStringBytes
        else:
            fileString[ 0 ] = 0
            startAddr = 0
        
        og_startAddr = startAddr
        
        fileString[ DXA_KEY_STRING_MAXLENGTH - 8: DXA_KEY_STRING_MAXLENGTH ] = bytearray(b'00000000')
        
        # 次にファイル名の文字列をセット
        
        src = nameTable[fileHead.nameAddress + 4:]
        amount = ( DXA_KEY_STRING_MAXLENGTH - 8 ) - og_startAddr
        end_string = min(src.find(0x0),amount-1)
        copied = src[:end_string]
        fileString[startAddr:startAddr+len(copied)] = copied
        startAddr = startAddr+len(copied)
        
        # その後にディレクトリの文字列をセット
        
        if directory.parentDirectoryAddress != 0xffffffffffffffff:
            while True:
                fileHead = DARC_FILEHEAD(fileTable[directory.directoryAddress:])
                src = nameTable[fileHead.nameAddress + 4:]
                amount = ( DXA_KEY_STRING_MAXLENGTH - 8 ) - og_startAddr
                end_string = min(src.find(0x0),amount-1)
                copied = src[:end_string]
                fileString[startAddr:startAddr+len(copied)] = copied
                startAddr = startAddr+len(copied)
                directory = DARC_DIRECTORY(directoryTable[directory.parentDirectoryAddress:])
                if directory.parentDirectoryAddress == 0xffffffffffffffff:
                    break
        
        new_key = fileString[:startAddr]
        return new_key
        

def main() -> None:
    decompiler = DXArchive()
    
    # DXArchive V8
    archivePath_v8 = Path("./test_wolf/version_2255.wolf")
    archivePath_v8 = Path("./test_wolf/version_2264.wolf")
    archivePath_v8 = Path("./test_wolf/version_2271.wolf")
    archivePath_v8 = Path("./test_wolf/version_2281.wolf")
    key_2_25_2_81 = bytearray([57, 0x4C, 0x46, 0x52, 0x50, 0x72, 0x4F, 0x21, 0x70, 0x28, 0x3B, 0x73, 0x35, 0x28, 0x28, 0x38, 0x50, 0x40, 0x28, 0x28, 0x55, 0x46, 0x57, 0x6C, 0x75, 0x24, 0x23, 0x35, 0x28, 0x3D])
    key_2_25_2_81 = bytearray(b"WLFRPrO!p(;s5((8P@((UFWlu$#5(=")
    
    
    # Setup
    archivePath = archivePath_v8
    keyString_ = key_2_25_2_81
    outputPath = Path("output")
    only_game_dat = True
    
    
    decompiled = decompiler.decodeArchive( archivePath=archivePath, outputPath=outputPath , only_game_dat=only_game_dat, keyString_=keyString_ )
    
    if decompiled:
        print(f"Decompiled {archivePath.name}")
    else:
        print(f"Couldn't decompile {archivePath.name}")


if __name__ == '__main__':
    main()
