# scel2txt

搜狗细胞词库转鼠须管（Rime）词库，使用 Python3 实现

## 使用

将从[搜狗官方词库网站](https://pinyin.sogou.com/dict/)下载的 `*.scel` 文件放入 `scel` 文件夹，然后运行

```bash
python3 scel2txt.py
```

可以得到:

* 后缀为 .txt 的同名词库文件
* 自动合并所有 *.txt 文件到 luna_pinyin.sogou.dict.yaml