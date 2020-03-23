"""
搜狗细胞词库转鼠须管（Rime）词库

搜狗的scel词库就是保存的文本的 unicode 编码，每两个字节一个字符（中文汉字或者英文字母）
找出其每部分的偏移位置即可
主要两部分
1.全局拼音表，貌似是所有的拼音组合，字典序
      格式为 (idx,len,pinyin) 的列表
      idx: 两个字节的整数 代表这个拼音的索引
      len: 两个字节的整数 拼音的字节长度
      pinyin: 当前的拼音，每个字符两个字节，总长 len

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

参考资料
1. https://raw.githubusercontent.com/archerhu/scel2mmseg/master/scel2mmseg.py
2. https://raw.githubusercontent.com/xwzhong/small-program/master/scel-to-txt/scel2txt.py
"""
import struct
import os
import sys


def read_utf16_str(f, offset=-1, len=2):
    if offset >= 0:
        f.seek(offset)
    string = f.read(len)
    return string.decode('UTF-16LE')


def read_uint16(f):
    return struct.unpack('<H', f.read(2))[0]


def get_hz_offset(f):
    mask = f.read(128)[4]
    if mask == 0x44:
        return 0x2628
    elif mask == 0x45:
        return 0x26c4
    else:
        sys.exit(1)


def get_dict_meta(f):
    title = read_utf16_str(f, 0x130, 0x338 - 0x130)
    category = read_utf16_str(f, 0x338, 0x540 - 0x338)
    desc = read_utf16_str(f, 0x540, 0xd40 - 0x540)
    samples = read_utf16_str(f, 0xd40, 0x1540 - 0xd40)
    return title, category, desc, samples


def get_py_map(f):
    py_map = {}
    f.seek(0x1540+4)

    while True:
        py_idx = read_uint16(f)
        py_len = read_uint16(f)
        py_str = read_utf16_str(f, -1, py_len)

        if py_idx not in py_map:
            py_map[py_idx] = py_str

        if py_str == 'zuo':
            break
    return py_map


def get_records(f, file_size, hz_offset, py_map):
    f.seek(hz_offset)
    records = []
    while f.tell() != file_size:
        word_count = read_uint16(f)
        pinyin_count = int(read_uint16(f) / 2)

        py_set = []
        for i in range(pinyin_count):
            py_id = read_uint16(f)
            if (py_map.get(py_id, None) == None):
                return records
            py_set.append(py_map[py_id])
        py_str = " ".join(py_set)

        for i in range(word_count):
            word_len = read_uint16(f)
            word_str = read_utf16_str(f, -1, word_len)
            f.read(12)
            records.append((py_str, word_str))
    return records


def get_words_from_sogou_cell_dict(fname):
    with open(fname, 'rb') as f:
        hz_offset = get_hz_offset(f)

        (title, category, desc, samples) = get_dict_meta(f)
        #print("title: %s\ncategory: %s\ndesc: %s\nsamples: %s" %
        #      (title, category, desc, samples))

        py_map = get_py_map(f)

        file_size = os.path.getsize(fname)
        words = get_records(f, file_size, hz_offset, py_map)
        return words


def save(records, f):
    records_translated = list(map(lambda x: "%s\t%s" % (
        x[1], x[0]), records))
    f.write("\n".join(records_translated))
    return records_translated


def main():
    # 将要转换的词库添加在 scel 目录下
    scel_files = list(filter(lambda x: x.endswith('.scel'), [
        i for i in os.listdir("./scel")]))

    dict_file = "luna_pinyin.sogou.dict.yaml"
    dict_file_content = []
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
    sougo_dict_name_list = list(
        map(lambda x: x.replace(".scel", ""), scel_files))
    dict_file_content.append(dict_file_header % ",".join(sougo_dict_name_list))

    for scel_file in scel_files:
        records = get_words_from_sogou_cell_dict(
            os.path.join("./scel", scel_file))
        print("%s: %s 个词" % (scel_file, len(records)))
        with open(os.path.join("./out", scel_file.replace(".scel", ".txt")), "w") as fout:
            dict_file_content.extend(save(records, fout))
        print("-"*80)

    print("合并后 %s: %s 个词" % (dict_file, len(dict_file_content) - 1))
    with open(os.path.join("./out", dict_file), "w") as dictfout:
        dictfout.write("\n".join(dict_file_content))


if __name__ == "__main__":
    main()
