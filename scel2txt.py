"""
搜狗细胞词库转鼠须管（Rime）词库

@see 解析逻辑见 https://raw.githubusercontent.com/xwzhong/small-program/master/scel-to-txt/scel2txt.py
"""

import sys
import os
import binascii
import struct
import pdb


class Scel2Txt(object):
    """
    搜狗的scel词库就是保存的文本的 unicode 编码，每两个字节一个字符（中文汉字或者英文字母）
    找出其每部分的偏移位置即可
    主要两部分
    1.全局拼音表，貌似是所有的拼音组合，字典序
          格式为 (index,len,pinyin) 的列表
          index: 两个字节的整数 代表这个拼音的索引
          len: 两个字节的整数 拼音的字节长度
          pinyin: 当前的拼音，每个字符两个字节，总长len
    
    2.汉语词组表
          格式为 (same,py_table_len,py_table,{word_len,word,ext_len,ext}) 的一个列表
          same: 两个字节 整数 同音词数量
          py_table_len:  两个字节 整数
          py_table: 整数列表，每个整数两个字节,每个整数代表一个拼音的索引
    
          word_len:两个字节 整数 代表中文词组字节数长度
          word: 中文词组,每个中文汉字两个字节，总长度 word_len
          ext_len: 两个字节 整数 代表扩展信息的长度，好像都是 10
          ext: 扩展信息 前两个字节是一个整数(不知道是不是词频) 后八个字节全是 0
    
         {word_len,word,ext_len,ext} 一共重复 same 次 同音词 相同拼音表
    """
    def __init__(self):
        # 拼音表偏移，
        self.startPy = 0x1540
        # 汉语词组表偏移
        self.startChinese = 0x2628
        # 全局拼音表
        self.GPy_Table = {}
        # 解析结果
        # 元组(词频,拼音,中文词组)的列表
        self.GTable = []

    def byte2str(self, data):
        '''将原始字节码转为字符串'''
        i = 0
        length = len(data)
        ret = u''
        while i < length:
            x = data[i:i+2]
            t = chr(struct.unpack('H', x)[0])
            if t == u'\r':
                ret += u'\n'
            elif t != u' ':
                ret += t
            i += 2
        return ret

    def getPyTable(self, data):
        # 获取拼音表
        if data[0:4] != b"\x9D\x01\x00\x00":
            return None
        data = data[4:]
        pos = 0
        length = len(data)
        while pos < length:
            index = struct.unpack('H', data[pos:pos+2])[0]
            pos += 2
            l = struct.unpack('H', data[pos:pos+2])[0]
            pos += 2
            py = self.byte2str(data[pos:pos+l])
            self.GPy_Table[index] = py
            pos += l

    def getWordPy(self, data):
        # 获取一个词组的拼音
        pos = 0
        length = len(data)
        ret = []
        while pos < length:
            index = struct.unpack('H', data[pos:pos+2])[0]
            ret.append(self.GPy_Table[index])
            pos += 2
        return " ".join(ret)

    def getWord(self, data):
        # 获取一个词组
        pos = 0
        length = len(data)
        ret = u''
        while pos < length:

            index = struct.unpack('H', data[pos:pos+2])[0]
            ret += GPy_Table[index]
            pos += 2
        return ret

    def getChinese(self, data):
        # 读取中文表
        pos = 0
        length = len(data)
        while pos < length:
            # 同音词数量
            same = struct.unpack('H', data[pos:pos+2])[0]

            # 拼音索引表长度
            pos += 2
            py_table_len = struct.unpack('H', data[pos:pos+2])[0]
            # 拼音索引表
            pos += 2
            py = self.getWordPy(data[pos: pos+py_table_len])

            # 中文词组
            pos += py_table_len
            for i in range(same):
                # 中文词组长度
                c_len = struct.unpack('H', data[pos:pos+2])[0]
                # 中文词组
                pos += 2
                word = self.byte2str(data[pos: pos + c_len])
                # 扩展数据长度
                pos += c_len
                ext_len = struct.unpack('H', data[pos:pos+2])[0]
                # 词频
                pos += 2
                count = struct.unpack('H', data[pos:pos+2])[0]
                # 保存
                self.GTable.append((count, py, word))
                # 到下个词的偏移位置
                pos += ext_len

    def deal(self, file_name):
        self.GTable = []
        print('-'*80)
        with open(file_name, 'rb') as fin:
            data = fin.read()
        if data[0:12] != b"\x40\x15\x00\x00\x44\x43\x53\x01\x01\x00\x00\x00":
            print("确认你选择的是搜狗(.scel)词库?")
            sys.exit(0)

        self.getPyTable(data[self.startPy:self.startChinese])
        self.getChinese(data[self.startChinese:])


if __name__ == '__main__':

    # 将要转换的词库添加在 scel 目录下
    scel_file_list = list(filter(lambda x: x.endswith('.scel'), [
                          i for i in os.listdir("./scel")]))
    scel2txt = Scel2Txt()

    dict_file = "luna_pinyin.sogou.dict.yaml"
    dict_txt = []
    dict_file_header = """# Rime dictionary
# encoding: utf-8
# 搜狗词库 目前包含如下:
# %s

---
name: luna_pinyin.sogou
version: "1.0"
sort: by_weight
use_preset_vocabulary: true
...
    """
    sougo_dict_list = list(map(lambda x: x.replace(".scel", ""), scel_file_list))
    dict_txt.append(dict_file_header % ",".join(sougo_dict_list))

    for scel_file in scel_file_list:
        scel2txt.deal(os.path.join("./scel", scel_file))
        result = list(map(lambda x: str(
            x[2]+"\t"+x[1]), scel2txt.GTable))
        dict_txt.extend(result)
        print("%s:%s 个词" % (scel_file, len(result)))
        with open(os.path.join("./out", scel_file.replace(".scel", ".txt")), "w") as fout:
            fout.write("\n".join(result))
    
    print("合并后 %s:%s 个词" % (dict_file,len(dict_txt)))
    with open(os.path.join("./out", dict_file), "w") as dictfout:
        dictfout.write("\n".join(dict_txt))
