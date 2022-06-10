#!/usr/bin/python
# -*- coding: utf-8 -*-

# data type ------------------------------------

# 数値ごとの出現数や算出されたエンコード後のビット列や、結合部分の情報等の構造体
import array


class HUFFMAN_NODE:
    def __init__(self):
        self.weight = 0  # 出現数( 結合データでは出現数を足したモノ )
        self.bitNum = 0  # 圧縮後のビット列のビット数( 結合データでは使わない )
        self.bitArray = array.array("I", [0] * 32)  # [32] ; # 圧縮後のビット列( 結合データでは使わない )
        self.index = 0  # 結合データに割り当てられた参照インデックス( 0 or 1 )
        self.parentNode = -1  # このデータを従えている結合データの要素配列のインデックス
        self.childNode = [
            0,
            0,
        ]  # [2]            # このデータが結合させた２要素の要素配列インデックス( 結合データではない場合はどちらも -1 )

    def __repr__(self) -> str:
        return f"""HUFFMAN_NODE
|- weight = {self.weight}
|- bitNum = {self.bitNum}
|- bitArray = {len(self.bitArray)}
|- index = {self.index}
|- parentNode = {self.parentNode}
|- childNode = {self.childNode}
"""


# ビット単位入出力用データ構造体
class BIT_STREAM:
    def __init__(self):
        self.buffer = array.array("B", [])
        self._bytes = array.array("Q", [])
        self.bits = None

    def __repr__(self) -> str:
        return f"""
BitStream.Buffer - {self.buffer.hex()[:20]}
BitStream.Bytes - {self._bytes}
BitStream.Bits - {self.bits}
"""


# code -----------------------------------------

# ビット単位入出力の初期化
def bitStream_Init(bitStream: BIT_STREAM, buffer, isRead: bool) -> BIT_STREAM:
    bitStream.buffer = buffer
    bitStream._bytes = 0
    bitStream.bits = 0
    if not isRead:
        bitStream.buffer[0] = 0

    return bitStream


# ビット単位の数値の書き込みを行う
def bitStream_Write(bitStream: BIT_STREAM, bitNum, outputData) -> BIT_STREAM:
    for i in range(bitNum):
        bitStream.buffer[bitStream._bytes] |= (
            (outputData >> (bitNum - 1 - i)) & 1
        ) << (7 - bitStream.bits)
        bitStream.bits += 1
        if bitStream.bits == 8:
            bitStream._bytes += 1
            bitStream.bits = 0
            bitStream.buffer[bitStream._bytes] = 0
    return bitStream


# ビット単位の数値の読み込みを行う
def bitStream_Read(bitStream: BIT_STREAM, bitNum) -> int:
    result = 0
    for i in range(bitNum):
        result = result | (
            ((bitStream.buffer[bitStream._bytes] >> (7 - bitStream.bits)) & 1)
        ) << (bitNum - 1 - i)
        # print(f"\t{result=}")
        bitStream.bits += 1
        if bitStream.bits == 8:
            bitStream._bytes += 1
            # print(f"\t{bitStream._bytes=}")
            bitStream.bits = 0
    # print("bitStream_Read ###############################################")
    return result


# 指定の数値のビット数を取得する
def bitStream_GetBitNum(data):
    for i in range(1, 64):
        if data < (1 << i):
            return i
    return i


# ビット単位の入出力データのサイズ( バイト数 )を取得する
def bitStream_GetBytes(bitStream: BIT_STREAM) -> int:
    if bitStream.bits != 0:
        bitStream._bytes += 1
    return bitStream._bytes


# データを圧縮
#
# 戻り値:圧縮後のサイズ  0 はエラー  Dest に NULL を入れると圧縮データ格納に必要なサイズが返る
def huffman_Encode(src, srcSize, dest=None) -> tuple:
    # print("Huffman_Encode()")
    # 結合データと数値データ、０～２５５までが数値データ
    # (結合データの数と圧縮するデータの種類の数を足すと必ず『種類の数＋(種類の数－１)』になる。
    # 『ホントか？』と思われる方はハフマン圧縮の説明で出てきたＡ,Ｂ,Ｃ,Ｄ,Ｅの結合部分の数を
    # 数えてみて下さい、種類が５つに対して結合部分は一つ少ない４つになっているはずです。
    # 種類が６つの時は結合部分は５つに、そして種類が２５６この時は結合部分は２５５個になります)

    # HUFFMAN_NODE Node[256 + 255]
    node = [HUFFMAN_NODE() for _ in range(256 + 255)]

    # void 型のポインタではアドレスの操作が出来ないので unsigned char 型のポインタにする
    srcPoint = src

    # 各数値の圧縮後のビット列を算出する
    if True:
        # print("\tBlock 1")
        # 数値データを初期化する
        for i in range(256):
            node[i].weight = 0  # 出現数はこれから算出するので０に初期化
            node[i].childNode[0] = -1  # 数値データが終点なので -1 をセットする
            node[i].childNode[1] = -1  # 数値データが終点なので -1 をセットする
            node[i].parentNode = -1  # まだどの要素とも結合されていないので -1 をセットする

        # 各数値の出現数をカウント
        for i in range(srcSize):
            node[srcPoint[i]].weight += 1

        # 出現数を 0～65535 の比率に変換する
        for i in range(256):
            node[i].weight = int(node[i].weight * 0xFFFF / srcSize)

        # 出現数の少ない数値データ or 結合データを繋いで
        # 新しい結合データを作成、全ての要素を繋いで残り１個になるまで繰り返す
        dataNum = 256  # 残り要素数
        nodeNum = 256  # 次に新しく作る結合データの要素配列のインデックス
        while dataNum > 1:
            if True:
                # 出現数値の低い要素二つを探す
                minNode1 = -1
                minNode2 = -1

                # 残っている要素全てを調べるまでループ
                nodeIndex = 0
                i = 0
                while (
                    i < dataNum
                ):  # "for i in range(dataNum)" would increment i even if we continue, so we use while to increment i ourselves
                    # もう既に何処かの要素と結合されている場合は対象外
                    if node[nodeIndex].parentNode != -1:
                        nodeIndex += 1
                        continue

                    i += 1

                    # まだ有効な要素をセットしていないか、より出現数値の
                    # 少ない要素が見つかったら更新
                    if minNode1 == -1 or node[minNode1].weight > node[nodeIndex].weight:
                        # 今まで一番出現数値が少なかったと思われた
                        # 要素は二番目に降格
                        minNode2 = minNode1
                        # 新しい一番の要素の要素配列のインデックスを保存
                        minNode1 = nodeIndex
                    else:
                        # 一番よりは出現数値が多くても、二番目よりは出現数値が
                        # 少ないかもしれないので一応チェック(又は二番目に出現数値の
                        # 少ない要素がセットされていなかった場合もセット)
                        if (
                            minNode2 == -1
                            or node[minNode2].weight > node[nodeIndex].weight
                        ):
                            minNode2 = nodeIndex
                    nodeIndex += 1

            # 二つの要素を繋いで新しい要素(結合データ)を作る
            # new_node = HUFFMAN_NODE()
            # node[i] = new_node

            node[nodeNum].parentNode = -1  # 新しいデータは当然まだ何処とも繋がっていないので -1
            node[nodeNum].weight = (
                node[minNode1].weight + node[minNode2].weight
            )  # 出現数値は二つの数値を足したものをセットする
            node[nodeNum].childNode = (
                minNode1,
                minNode2,
            )  # この結合部で 0 を選んだら出現数値が一番少ない要素に繋がる
            # node[nodeNum].childNode[0] = minNode1    # この結合部で 1 を選んだら出現数値が二番目に少ない要素に繋がる
            # node[nodeNum].childNode[1] = minNode2    # この結合部で 1 を選んだら出現数値が二番目に少ない要素に繋がる

            # 結合された要素二つに、自分達に何の値が割り当てられたかをセットする
            node[minNode1].index = 0  # 一番出現数値が少ない要素は 0 番
            node[minNode2].index = 1  # 二番目に出現数値が少ない要素は 1 番

            # 結合された要素二つに、自分達を結合した結合データの要素配列インデックスをセットする
            node[minNode1].parentNode = nodeNum
            node[minNode2].parentNode = nodeNum

            # 要素の数を一個増やす
            nodeNum += 1

            # 残り要素の数は、一つ要素が新しく追加された代わりに
            # 二つの要素が結合されて検索の対象から外れたので
            # 結果 1 - 2 で -1
            dataNum -= 1

    if True:
        # print("\tBlock 1.2")
        # 各数値の圧縮後のビット列を割り出す
        tempBitArray = bytearray([0] * 32)

        # 数値データの種類の数だけ繰り返す
        for i in range(256):
            # 数値データから結合データを上へ上へと辿ってビット数を数える

            # ビット数を初期化しておく
            node[i].bitNum = 0

            # 一時的に数値データから遡っていったときのビット列を保存する処理の準備
            tempBitIndex = 0
            tempBitCount = 0
            tempBitArray[tempBitIndex] = 0

            # 何処かと結合されている限りカウントし続ける(天辺は何処とも結合されていないので終点だと分かる)
            nodeIndex = i
            while node[nodeIndex].parentNode != -1:
                # 配列要素一つに入るビットデータは８個なので、同じ配列要素に
                # 既に８個保存していたら次の配列要素に保存先を変更する
                if tempBitCount == 8:
                    tempBitCount = 0
                    tempBitIndex += 1
                    tempBitArray[tempBitIndex] = 0

                # 新しく書き込む情報で今までのデータを上書きしてしまわないように１ビット左にシフトする
                tempBitArray[tempBitIndex] <<= 1

                # 結合データに割り振られたインデックスを最下位ビット(一番右側のビット)に書き込む
                # TempBitArray[TempBitIndex] |= (unsigned char)Node[NodeIndex].Index
                tempBitArray[tempBitIndex] |= (
                    node[nodeIndex].index % 256
                )  # % 256 might be unnecessary?

                # 保存したビット数を増やす
                tempBitCount += 1

                # ビット数を増やす
                node[i].bitNum += 1

                nodeIndex = node[nodeIndex].parentNode

            # TempBitArray に溜まったデータは数値データから結合データを天辺に向かって
            # 上へ上へと遡っていった時のビット列なので、逆さまにしないと圧縮後のビット
            # 配列として使えない(展開時に天辺の結合データから数値データまで辿ることが
            # 出来ない)ので、順序を逆さまにしたものを数値データ内のビット列バッファに保存する

            bitCount = 0
            bitIndex = 0

            # 最初のバッファを初期化しておく
            # (全部 論理和(or)演算 で書き込むので、最初から１になっている
            # ビットに０を書き込んでも１のままになってしまうため)
            node[i].bitArray[bitIndex] = 0

            # 一時的に保存しておいたビット列の最初まで遡る
            while tempBitIndex >= 0:
                # 書き込んだビット数が一つの配列要素に入る８ビットに
                # 達してしまったら次の配列要素に移る
                if bitCount == 8:
                    bitCount = 0
                    bitIndex += 1
                    node[i].bitArray[bitIndex] = 0

                # まだ何も書き込まれていないビットアドレスに１ビット書き込む
                node[i].bitArray[bitIndex] |= (
                    (tempBitArray[tempBitIndex] & 1) << bitCount
                ) % 256  # % 256 might be unnecessary?

                # 書き込み終わったビットはもういらないので次のビットを
                # 書き込めるように１ビット右にシフトする
                tempBitArray[tempBitIndex] >>= 1

                # １ビット書き込んだので残りビット数を１個減らす
                tempBitCount -= 1

                # もし現在書き込み元となっている配列要素に書き込んでいない
                # ビット情報が無くなったら次の配列要素に移る
                if tempBitCount == 0:
                    tempBitIndex -= 1
                    tempBitCount = 8

                # 書き込んだビット数を増やす
                bitCount += 1

    # 変換処理
    if True:
        # print("\tBlock 2")
        # 圧縮データを格納するアドレスをセット
        # (圧縮データ本体は元のサイズ、圧縮後のサイズ、各数値の出現数等を
        # 格納するデータ領域の後に格納する)
        pressData = bytearray(dest)

        # 圧縮するデータの参照アドレスを初期化
        srcSizeCounter = 0

        # 圧縮したデータの参照アドレスを初期化
        pressSizeCounter = 0

        # 圧縮したビットデータのカウンタを初期化
        pressBitCounter = 0

        # 圧縮データの最初のバイトを初期化しておく
        if dest is not None:
            # pressData[pressSizeCounter] = 0
            pressData.append(0)

        # 圧縮対照のデータを全て圧縮後のビット列に変換するまでループ
        # for( srcSizeCounter = 0 ; srcSizeCounter < srcSize ; srcSizeCounter ++ )
        while srcSizeCounter < srcSize:

            # 保存する数値データのインデックスを取得
            nodeIndex = srcPoint[srcSizeCounter]

            # 指定の数値データの圧縮後のビット列を出力

            # 参照する配列のインデックスを初期化
            bitIndex = 0

            # 配列要素中の出力したビット数の初期化
            bitNum = 0

            # 最初に書き込むビット列の配列要素をセット
            bitData = node[nodeIndex].bitArray[0]

            # 全てのビットを出力するまでループ
            bitCounter = 0
            while bitCounter < node[nodeIndex].bitNum:
                # もし書き込んだビット数が８個になっていたら次の配列要素に移る
                if pressBitCounter == 8:
                    pressSizeCounter += 1
                    if dest is not None:
                        # pressData[pressSizeCounter] = 0
                        pressData.append(0)

                    pressBitCounter = 0

                # もし書き出したビット数が８個になっていたら次の配列要素に移る
                if bitNum == 8:
                    bitIndex += 1
                    bitData = node[nodeIndex].bitArray[bitIndex]
                    bitNum = 0

                # まだ何も書き込まれていないビットアドレスに１ビット書き込む
                if dest is not None:
                    pressData[pressSizeCounter] |= (
                        (bitData & 1) << pressBitCounter
                    ) % 256  # % 256 might be unnecessary?

                # 書き込んだビット数を増やす
                pressBitCounter += 1

                # 次に書き出すビットを最下位ビット(一番右のビット)にする為に
                # １ビット右シフトする
                bitData >>= 1

                # 書き出したビット数を増やす
                bitNum += 1

                bitCounter += 1

            srcSizeCounter += 1

        # 最後の１バイト分のサイズを足す
        pressSizeCounter += 1

    dest = pressData  # Because in c++ it's a pointer or something, I don't know C

    # 圧縮データの情報を保存する
    if True:
        # print("\tBlock 3")
        # u8 HeadBuffer[ 256 * 2 + 32 ]
        headBuffer = array.array("B", [0] * (256 * 2 + 32))

        # s32 WeightSaveData[ 256 ]
        weightSaveData = [0] * 256

        bitStream = BIT_STREAM()
        bitStream = bitStream_Init(bitStream, headBuffer, False)

        # 元のデータのサイズをセット
        bitNum = bitStream_GetBitNum(srcSize)

        if bitNum > 0:
            bitNum -= 1
        bitStream = bitStream_Write(bitStream, 6, bitNum)
        bitStream = bitStream_Write(bitStream, bitNum + 1, srcSize)
        # 圧縮後のデータのサイズをセット
        bitNum = bitStream_GetBitNum(pressSizeCounter)
        bitStream = bitStream_Write(bitStream, 6, bitNum)
        bitStream = bitStream_Write(bitStream, bitNum + 1, pressSizeCounter)

        # 各数値の出現率の差分値を保存する
        weightSaveData[0] = node[0].weight
        for i in range(1, 256):
            weightSaveData[i] = node[i].weight - node[i - 1].weight

        for i in range(256):
            minus = True

            if weightSaveData[i] < 0:
                outputNum = -weightSaveData[i]
                minus = True
            else:
                outputNum = weightSaveData[i]
                minus = False

            bitNum = int((bitStream_GetBitNum(outputNum) + 1) / 2)
            if bitNum > 0:
                bitNum -= 1

            bitStream = bitStream_Write(bitStream, 3, bitNum)
            bitStream = bitStream_Write(bitStream, 1, int(minus))
            bitStream = bitStream_Write(bitStream, (bitNum + 1) * 2, outputNum)

        # ヘッダサイズを取得
        headBuffer = (
            bitStream.buffer
        )  # Stupid C and it's pointers and references and whatnot
        headSize = bitStream_GetBytes(bitStream)

        total = pressSizeCounter + headSize

        temp = bytearray([0] * total)

        # 圧縮データの情報を圧縮データにコピーする
        if dest is not None:
            # ヘッダの分だけ移動
            #
            # Maybe this is just headBuffer+dest
            # Maybe this is just headBuffer.axtend(dest)
            #
            j = pressSizeCounter - 1
            while j >= 0:
                # print(f"ON {headSize+j} -> {dest[j]}")
                # ( ( u8 * )Dest )[ HeadSize + j ] = ( ( u8 * )Dest )[ j ]
                # dest[headSize+j] = dest[j]
                temp[headSize + j] = dest[j]
                temp[j] = dest[j]
                if j == 0:
                    break
                j -= 1

            # ヘッダを書き込み
            # memcpy( Dest, HeadBuffer, ( size_t )HeadSize )
            """
            mayor = max(len(temp),len(temp[:headSize]),len(headBuffer))
            #print(f"idx\ttemp{len(temp)}\t\ttemp2{len(temp[:headSize])}\thead{len(headBuffer)}")
            for x in range(mayor):
                try:
                    a = temp[x]
                except IndexError:
                    a = ' '
                try:
                    b = temp[:headSize][x]
                except IndexError:
                    b = ' '
                try:
                    c = headBuffer[x]
                except IndexError:
                    c = ' '

                #print(f"{x}\t{a}\t\t{b}\t\t{c}")
            """

            # for i in range(headSize):
            #     headBuffer[i+headSize] = temp[i]

            # dest = headBuffer[:headSize] + temp[:headSize]

            for idx, x in enumerate(headBuffer[:headSize]):
                temp[idx] = x

            dest = temp

    # 圧縮後のサイズを返す
    return (dest, pressSizeCounter + headSize)


def huffman_Decode(press, dest=None) -> tuple:
    # 結合データと数値データ、０～２５５までが数値データ
    node = [HUFFMAN_NODE() for _ in range(256 + 255)]

    # u16 Weight[ 256 ] ;
    weight = array.array("H", [0] * 256)

    # void 型のポインタではアドレスの操作が出来ないので unsigned char 型のポインタにする
    pressPoint = press
    destPoint = dest

    # 圧縮データの情報を取得する
    if True:
        bitStream = BIT_STREAM()
        bitStream = bitStream_Init(bitStream, pressPoint, True)

        originalSize = bitStream_Read(
            bitStream, (bitStream_Read(bitStream, 6) + 1) % 256
        )
        pressSize = bitStream_Read(bitStream, (bitStream_Read(bitStream, 6) + 1) % 256)

        # 出現頻度のテーブルを復元する
        bitNum = (bitStream_Read(bitStream, 3) + 1) * 2
        minus = bitStream_Read(bitStream, 1)
        saveData = bitStream_Read(bitStream, bitNum)
        weight[0] = saveData
        for i in range(1, 256):
            bitNum = (bitStream_Read(bitStream, 3) + 1) * 2
            minus = bitStream_Read(bitStream, 1)
            saveData = bitStream_Read(bitStream, bitNum)
            if minus == 1:
                weight[i] = (weight[i - 1] - saveData) % 2**16
            else:
                weight[i] = (weight[i - 1] + saveData) % 2**16

        # ヘッダサイズを取得
        headSize = bitStream_GetBytes(bitStream)

    # Dest が NULL の場合は 解凍後のデータのサイズを返す
    if dest is None:
        return originalSize

    # 解凍後のデータのサイズを取得する
    destSize = originalSize

    # print(f"{originalSize=}")
    # print(f"{destSize=}")

    # 各数値の結合データを構築する
    if True:
        # 数値データを初期化する
        for i in range(256 + 255):
            try:
                _weight = weight[i]
            except IndexError:
                _weight = 0
            node[i].weight = _weight  # 出現数は保存しておいたデータからコピー
            node[i].childNode[0] = -1  # 数値データが終点なので -1 をセットする
            node[i].childNode[1] = -1  # 数値データが終点なので -1 をセットする
            node[i].parentNode = -1  # まだどの要素とも結合されていないので -1 をセットする

        # 出現数の少ない数値データ or 結合データを繋いで
        # 新しい結合データを作成、全ての要素を繋いで残り１個になるまで繰り返す
        # (圧縮時と同じコードです)
        dataNum = 256  # 残り要素数
        nodeNum = 256  # 次に新しく作る結合データの要素配列のインデックス
        while dataNum > 1:
            # 出現数値の低い要素二つを探す
            minNode1 = -1
            minNode2 = -1

            # 残っている要素全てを調べるまでループ
            nodeIndex = 0
            i = 0
            while i < dataNum:
                if node[nodeIndex].parentNode != -1:
                    nodeIndex += 1
                    continue

                i += 1

                # まだ有効な要素をセットしていないか、より出現数値の
                # 少ない要素が見つかったら更新
                if minNode1 == -1 or node[minNode1].weight > node[nodeIndex].weight:
                    # 今まで一番出現数値が少なかったと思われた
                    # 要素は二番目に降格
                    minNode2 = minNode1

                    # 新しい一番の要素の要素配列のインデックスを保存
                    minNode1 = nodeIndex
                else:
                    # 一番よりは出現数値が多くても、二番目よりは出現数値が
                    # 少ないかもしれないので一応チェック(又は二番目に出現数値の
                    # 少ない要素がセットされていなかった場合もセット)
                    if minNode2 == -1 or node[minNode2].weight > node[nodeIndex].weight:
                        minNode2 = nodeIndex
                nodeIndex += 1

            # 二つの要素を繋いで新しい要素(結合データ)を作る
            node[nodeNum].parentNode = -1  # 新しいデータは当然まだ何処とも繋がっていないので -1
            node[nodeNum].weight = (
                node[minNode1].weight + node[minNode2].weight
            )  # 出現数値は二つの数値を足したものをセットする
            node[nodeNum].childNode[0] = minNode1  # この結合部で 0 を選んだら出現数値が一番少ない要素に繋がる
            node[nodeNum].childNode[1] = minNode2  # この結合部で 1 を選んだら出現数値が二番目に少ない要素に繋がる

            # 結合された要素二つに、自分達に何の値が割り当てられたかをセットする
            node[minNode1].index = 0  # 一番出現数値が少ない要素は 0 番
            node[minNode2].index = 1  # 二番目に出現数値が少ない要素は 1 番

            # 結合された要素二つに、自分達を結合した結合データの要素配列インデックスをセットする
            node[minNode1].parentNode = nodeNum
            node[minNode2].parentNode = nodeNum

            # 要素の数を一個増やす
            nodeNum += 1

            # 残り要素の数は、一つ要素が新しく追加された代わりに
            # 二つの要素が結合されて検索の対象から外れたので
            # 結果 1 - 2 で -1
            dataNum -= 1

        # 各数値の圧縮時のビット列を割り出す
        if True:
            tempBitArray = bytearray([0] * 32)

            # 数値データと結合データの数だけ繰り返す
            for i in range(256 + 254):
                # 数値データから結合データを上へ上へと辿ってビット数を数える
                # ビット数を初期化しておく
                node[i].bitNum = 0

                # 一時的に数値データから遡っていったときのビット列を保存する処理の準備
                tempBitIndex = 0
                tempBitCount = 0
                tempBitArray[tempBitIndex] = 0

                # 何処かと結合されている限りカウントし続ける(天辺は何処とも結合されていないので終点だと分かる)
                nodeIndex = i
                while node[nodeIndex].parentNode != -1:
                    # 配列要素一つに入るビットデータは８個なので、同じ配列要素に
                    # 既に８個保存していたら次の配列要素に保存先を変更する
                    if tempBitCount == 8:
                        tempBitCount = 0
                        tempBitIndex += 1
                        tempBitArray[tempBitIndex] = 0

                    # 新しく書き込む情報で今までのデータを上書きしてしまわないように１ビット左にシフトする
                    tempBitArray[tempBitIndex] <<= 1

                    # 結合データに割り振られたインデックスを最下位ビット(一番右側のビット)に書き込む
                    tempBitArray[tempBitIndex] |= (
                        node[nodeIndex].index % 256
                    )  # % 256 might be unnecessary?

                    # 保存したビット数を増やす
                    tempBitCount += 1

                    # ビット数を増やす
                    node[i].bitNum += 1

                    nodeIndex = node[nodeIndex].parentNode

                # TempBitArray に溜まったデータは数値データから結合データを天辺に向かって
                # 上へ上へと遡っていった時のビット列なので、逆さまにしないと圧縮後のビット
                # 配列として使えない(展開時に天辺の結合データから数値データまで辿ることが
                # 出来ない)ので、順序を逆さまにしたものを数値データ内のビット列バッファに保存する
                bitCount = 0
                bitIndex = 0

                # 最初のバッファを初期化しておく
                # (全部 論理和(or)演算 で書き込むので、最初から１になっている
                # ビットに０を書き込んでも１のままになってしまうため)
                node[i].bitArray[bitIndex] = 0

                # 一時的に保存しておいたビット列の最初まで遡る
                while tempBitIndex >= 0:
                    # 書き込んだビット数が一つの配列要素に入る８ビットに
                    # 達してしまったら次の配列要素に移る
                    if bitCount == 8:
                        bitCount = 0
                        bitIndex += 1
                        node[i].bitArray[bitIndex] = 0

                    # まだ何も書き込まれていないビットアドレスに１ビット書き込む
                    node[i].bitArray[bitIndex] |= (
                        tempBitArray[tempBitIndex] & 1
                    ) << bitCount % 256  # % 256 might be unnecessary?
                    # print(f"node[i].bitArray[bitIndex] = {node[i].bitArray[bitIndex]}")

                    # 書き込み終わったビットはもういらないので次のビットを
                    # 書き込めるように１ビット右にシフトする
                    tempBitArray[tempBitIndex] >>= 1

                    # １ビット書き込んだので残りビット数を１個減らす
                    tempBitCount -= 1

                    # もし現在書き込み元となっている配列要素に書き込んでいない
                    # ビット情報が無くなったら次の配列要素に移る
                    if tempBitCount == 0:
                        tempBitIndex -= 1
                        tempBitCount = 8

                    # 書き込んだビット数を増やす
                    bitCount += 1

    # 解凍処理
    if True:
        # unsigned char *PressData ;

        nodeIndexTable = [0] * 512

        # 各ビット配列がどのノードに繋がるかのテーブルを作成する
        # u16 BitMask[ 9 ]
        bitMask = array.array("H", [0] * 9)

        for i in range(9):
            bitMask[i] = (1 << (i + 1)) - 1

        for i in range(512):
            nodeIndexTable[i] = -1

            # ビット列に適合したノードを探す
            for j in range(256 + 254):
                bitArray01 = bytearray()

                if node[j].bitNum > 9:
                    continue

                bitArray01 = node[j].bitArray[0] | (node[j].bitArray[1] << 8)
                if (i & bitMask[node[j].bitNum - 1]) == (
                    bitArray01 & bitMask[node[j].bitNum - 1]
                ):
                    nodeIndexTable[i] = j
                    break
        # 圧縮データ本体の先頭アドレスをセット
        # (圧縮データ本体は元のサイズ、圧縮後のサイズ、各数値の出現数等を
        # 格納するデータ領域の後にある)

        #
        #   (unsigned char *)  PressPoint
        #   u64                HeadSize
        #   unsigned long long HeadSize
        #

        # Byte shifting ????

        pressData = pressPoint[headSize:]

        # 解凍したデータの格納アドレスを初期化
        destSizeCounter = 0

        # 圧縮データの参照アドレスを初期化
        pressSizeCounter = 0

        # 圧縮ビットデータのカウンタを初期化
        pressBitCounter = 0

        # 圧縮データの１バイト目をセット
        pressBitData = pressData[pressSizeCounter]

        # 圧縮前のデータサイズになるまで解凍処理を繰り返す

        for destSizeCounter in range(destSize):
            # ビット列から数値データを検索する
            # 最後の17byte分のデータは天辺から探す( 最後の次のバイトを読み出そうとしてメモリの不正なアクセスになる可能性があるため )
            if destSizeCounter >= destSize - 17:
                # 結合データの天辺は一番最後の結合データが格納される５１０番目(０番から数える)
                # 天辺から順に下に降りていく
                nodeIndex = 510
            else:
                # それ以外の場合はテーブルを使用する
                # もし PressBitData に格納されている全ての
                # ビットデータを使い切ってしまった場合は次の
                # ビットデータをセットする
                if pressBitCounter == 8:
                    pressSizeCounter += 1
                    pressBitData = pressData[pressSizeCounter]
                    pressBitCounter = 0

                # 圧縮データを9bit分用意する
                tmp1 = pressData[pressSizeCounter + 1]
                pressBitData = (pressBitData | (tmp1 << (8 - pressBitCounter))) & 0x1FF
                # テーブルから最初の結合データを探す
                nodeIndex = nodeIndexTable[pressBitData]

                # 使った分圧縮データのアドレスを進める
                pressBitCounter += node[nodeIndex].bitNum
                if pressBitCounter >= 16:
                    pressSizeCounter += 2
                    pressBitCounter -= 16
                    pressBitData = pressData[pressSizeCounter] >> pressBitCounter
                elif pressBitCounter >= 8:
                    pressSizeCounter += 1
                    pressBitCounter -= 8
                    pressBitData = pressData[pressSizeCounter] >> pressBitCounter
                else:
                    pressBitData >>= node[nodeIndex].bitNum

            # 数値データに辿り着くまで結合データを下りていく
            while nodeIndex > 255:
                # もし PressBitData に格納されている全ての
                # ビットデータを使い切ってしまった場合は次の
                # ビットデータをセットする
                if pressBitCounter == 8:
                    pressSizeCounter += 1
                    pressBitData = pressData[pressSizeCounter]
                    pressBitCounter = 0

                # １ビット取得する
                index = pressBitData & 1

                # 使用した１ビット分だけ右にシフトする
                pressBitData >>= 1

                # 使用したビット数を一個増やす
                pressBitCounter += 1

                # 次の要素(結合データか数値データかはまだ分からない)に移る
                nodeIndex = node[nodeIndex].childNode[index]

            # 辿り着いた数値データを出力
            destPoint[destSizeCounter] = nodeIndex

    dest = destPoint
    # 解凍後のサイズを返す
    return (dest, originalSize)


def main():
    source = b"Lorem ipsum dolor sit amet consectetur adipisicing elit. Molestias earum mollitia iure consequatur minima magnam nesciunt, similique dicta quasi ipsam minus aliquid laudantium labore, fuga ad facere alias ea adipisci"
    # with open("test.html", mode="rb") as fp:
    #     source = fp.read()

    print(f"Encoding string with length {len(source)}")
    dest = array.array("I", [])
    dest, size = huffman_Encode(source, len(source), dest)
    print(f"Encoded to length {size}")

    originalSize = huffman_Decode(dest, None)

    print(f"We need buffer with length {originalSize}")

    dest_b = array.array("I", [0] * originalSize)
    dest_b, originalSize = huffman_Decode(dest, dest_b)

    print("".join([chr(x) for x in dest_b]))


if __name__ == "__main__":
    main()
