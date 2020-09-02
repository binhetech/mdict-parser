import pandas as pd
import re
import bs4
from bs4 import BeautifulSoup
from readmdict import MDX, MDD
import json
import unicodedata

tagSets = set()


def text_norm(text, lang):
    """
    文本规范化.
    """
    if lang == "en" or lang == "english":
        text = " ".join(text.strip().split())
    else:
        text = text.strip()
        text = unicodedata.normalize("NFKC", text)
    return text


def get_tag_list(node):
    return [i.name for i in node if isinstance(i, bs4.element.Tag)]


def get_audio(tags, pos, source, name="pron-g"):
    audios = []
    for i in tags:
        audio = {
            "name": i.find_all(name)[0].get_text(),
            "audioUrl": i.find_all("a")[0].attrs["href"],
            "country": i.find_all(re.compile("label"))[0].get_text(),
            "source": source, "pos": pos
        }
        audios.append(audio)
    return audios


def split_node_en_ch(tags):
    # 获取标签列表：[i.name for i in v.children if isinstance(i, bs4.element.Tag)]
    chs, ens = [], []
    for v in tags:
        # 根据标签提取， chn: 先把中文提出，并从树中移除
        vv = v
        ch = unicodedata.normalize("NFKC", vv.chn.extract().get_text())
        # 再提取全部英文，可解决标点无法提取问题
        # 根据属性提取
        en = vv.get_text()
        chs.append(ch.strip())
        ens.append(en.strip())
    return chs, ens


def parse_sentences(node, source):
    sentences = []
    chs, ens = split_node_en_ch(node)
    for ch, en in zip(chs, ens):
        sentence = {"chinese": ch, "english": en,
                    "audioUrlUS": "", "audioUrlUK": "", "source": source}
        sentences.append(sentence)
    return sentences


def get_sn(m, source):
    for t in get_tag_list(m):
        tagSets.add(t)
    # print("m=", get_tag_list(m))
    # 释义信息1
    # xr-gs; = soap opera
    # gram-g: [countable]
    # label-g-blk: (informal)
    # 提取词性小类
    if m.find_all("gram-g"):
        category = m.find_all("gram-g")[0].get_text()
    else:
        category = ""
    # 提取应用场景
    if m.find_all("label-g-blk"):
        scene = m.find_all("label-g-blk")[0].get_text()
    else:
        scene = ""
    # xr-gs： = 同义词
    xdef = m.find_all("def")
    chs, ens = split_node_en_ch(xdef)
    # 例句列表
    xgs = m.find_all("x-gs")
    sents = []
    for n in xgs:
        for t in get_tag_list(m):
            tagSets.add(t)
        # print("n=", get_tag_list(n))
        xgblk = n.find_all("x")
        # 3个例句
        sentences = parse_sentences(xgblk, source)
        sents += sentences
    paras = {"chinese": chs[0] if chs else "", "english": ens[0] if ens else "",
             "category": category, "scene": scene,
             "Sentences": sents, "source": source}
    return paras


def get_cixing(tags, source):
    phoneticsymbols = []
    paraphrases = []
    for i in tags:
        for t in get_tag_list(i):
            tagSets.add(t)
        # 词性
        pos = i.attrs["id"]
        # 提取美英音标、音频url
        if not phoneticsymbols:
            phoneticsymbols = get_audio(i.find_all("pron-g-blk"), pos, source)
        # 词性小类

        # 动词释义
        if i.find_all("vp-g"):
            # root词根、第三人称单数vp-g-ps
            wdVp = get_vp(i.find_all("vp-g"))
        if i.find_all("vpform"):
            # present simple一般现在时
            wdVpForm = i.find_all("vpform")[0].get_text()

        # 释义列表
        for m in i.find_all("sn-g"):
            # 获取释义、例句列表
            paras = get_sn(m, source)
            paras["pos"] = pos
            paraphrases.append(paras)
    return phoneticsymbols, paraphrases


def get_vp(tags):
    # 获取动词的各种形式
    vps = []
    for i in tags:
        vps.append({"form": i.attrs["form"], "text": i.find_all("vp")[0].get_text()})
    return vps


def get_sns(tags):
    # label, def, sn
    label = tags.find_all("label")[0].get_text()
    return


def get_pv(tags, source):
    """
    phrasal verbs动词短语.

    """
    # 获取短语搭配
    outs = []
    # 短语列表
    for i in tags:
        # 释义列表
        paraphrases = []
        for j in i.find_all("sn-g"):
            # 例句列表
            paras = get_sn(j, source)
            paras["pos"] = ""
            paraphrases.append(paras)
        outs.append({"phrase": i.find_all("pv")[0].get_text(),
                     "ParaPhrases": paraphrases})
    return outs


def parse_oxld(lexicon, bs, source="oxld_9"):
    if len(lexicon.split()) > 1:
        lexcionType = "Phrase"
    else:
        lexcionType = "Word"
    result = {"Lexicon": lexicon, "type": lexcionType}
    phoneticsymbols = []
    paraphrases = []
    vpg = []
    pvg = []

    print(get_tag_list(bs))

    # 获取词性部分（音标，释义，例句）
    if bs.find_all("div", "cixing_part", recursive=False):
        phoneticsymbols, paraphrases = get_cixing(bs.find_all("div", "cixing_part", recursive=False), source)

    # verb past动词时态
    if bs.find_all("vp-g", recursive=False):
        vpg = get_vp(bs.find_all("vp-g", recursive=False))

    # phrasal verbs动词短语
    if bs.find_all("pv-gs-blk", recursive=False):
        for tag in bs.find_all("pv-gs-blk", recursive=False):
            pvg += get_pv(tag.find_all("pv-g"), source)

    result["PhoneticSymbols"] = phoneticsymbols
    result["ParaPhrases"] = paraphrases
    result["Inflection"] = vpg
    result["PhrasalVerbs"] = pvg
    return result


def parse_jianming(lexicon, bs, source="jianming"):
    """
    简明英汉汉英词典
    """
    if len(lexicon.split()) > 1:
        lexcionType = "Phrase"
    else:
        lexcionType = "Word"
    result = {"Lexicon": lexicon, "type": lexcionType}
    phoneticsymbols = []
    paraphrases = []

    contents = bs.find_all(["font", "b"])
    newpos = ""
    newpp = ""
    sentences = []
    curIc = 0
    for ic, i in enumerate(contents):
        if ic < curIc:
            continue
        if i.name == "font" and i.attrs["color"] == "DarkMagenta":
            # 新词性
            newpos = i.get_text()
        elif i.name == "b":
            # 新释义
            newpp = i.get_text()
            if ic + 1 < len(contents):
                notSent = (contents[ic + 1].name == "font" and contents[ic + 1].attrs["color"] == "DarkMagenta") or \
                          contents[ic + 1].name == "b"
                if notSent:
                    if newpos != "" and newpp != "":
                        paras = {"pos": newpos, "english": "", "chinese": newpp, "Sentences": sentences,
                                 "source": source,
                                 "scene": "", "category": ""}
                        paraphrases.append(paras)
                        sentences = []
            elif ic + 1 == len(contents):
                if newpos != "" and newpp != "":
                    paras = {"pos": newpos, "english": "", "chinese": newpp, "Sentences": sentences, "source": source,
                             "scene": "", "category": ""}
                    paraphrases.append(paras)
                    sentences = []
        elif i.name == "font" and i.attrs["color"] == "Navy":
            # 添加例句
            en = i.get_text().strip()
            ch = contents[ic + 1].get_text().strip()
            if newpos != "" and newpp != "" and en != "" and ch != "":
                sentence = {"english": text_norm(en, "english"), "chinese": text_norm(ch, "chinese"), "audioUrlUS": "",
                            "audioUrlUK": "", "source": source}
                sentences.append(sentence)
            # 只有当下一个不是例句时：append释义信息
            if ic + 2 < len(contents):
                notSent = (contents[ic + 2].name == "font" and contents[ic + 2].attrs["color"] == "DarkMagenta") or \
                          contents[ic + 2].name == "b"
                if notSent:
                    if newpos != "" and newpp != "":
                        paras = {"pos": newpos, "english": "", "chinese": newpp, "Sentences": sentences,
                                 "source": source,
                                 "scene": "", "category": ""}
                        paraphrases.append(paras)
                        sentences = []
            elif ic + 2 == len(contents):
                if newpos != "" and newpp != "":
                    paras = {"pos": newpos, "english": "", "chinese": newpp, "Sentences": sentences, "source": source,
                             "scene": "", "category": ""}
                    paraphrases.append(paras)
                    sentences = []
            curIc = ic + 2

    result["PhoneticSymbols"] = phoneticsymbols
    result["ParaPhrases"] = paraphrases
    return result


def parse_item(item, source, item2infos):
    bs = BeautifulSoup(item2infos[item], "html.parser")
    # print(bs.prettify())
    result = {}
    if "oxld" in source:
        result = parse_oxld(item, bs, source)
    elif "jianming" in source:
        result = parse_jianming(item, bs, source)
    return result


def parse_items(items, source, item2infos):
    results = []
    for i in items:
        result = parse_item(i, source, item2infos)
        if result:
            results.append(result)
    return results


def write_json(infos, fileOut):
    print("{} lexicons writing...".format(len(infos)))
    with open(fileOut, "w", encoding="utf-8") as f:
        json.dump(infos, f, ensure_ascii=False)


def gen_dict(fileIn, source):
    mdx = MDX(fileIn)
    items = [i for i in mdx.items()]
    print("{} items loaded from {}".format(len(items), fileIn))
    item2infos = {i[0].decode("utf-8"): i[1].decode("utf-8") for i in items}
    # outs = parse_items(["sorb", "weird"], source, item2infos)
    outs = []
    for i in items:
        try:
            out = parse_item(i[0].decode("utf-8"), source, item2infos)
            if out["PhoneticSymbols"] or out["ParaPhrases"]:
                outs.append(out)
        except Exception as e:
            print("Error: {}".format(repr(e)))
    write_json(outs, f"./output/dict_{len(outs)}_{source}_output.json")


def test(fileIn, source):
    mdx = MDX(fileIn)
    items = [i for i in mdx.items()]
    print("{} items loaded from {}".format(len(items), fileIn))
    item2infos = {i[0].decode("utf-8"): i[1].decode("utf-8") for i in items}
    outs = parse_items(["sorb", "weird"], source, item2infos)
    # outs = []
    # for i in items:
    #     try:
    #         out = parse_item(i[0].decode("utf-8"), source, item2infos)
    #         if out["PhoneticSymbols"] or out["ParaPhrases"]:
    #             outs.append(out)
    #     except Exception as e:
    #         print("Error: {}".format(repr(e)))
    write_json(outs, f"./output/dict_output.json")


def test_jianming():
    fileIn = r'D:\work\database\dict\简明英汉汉英词典.mdx'
    source = "jianming-2"
    test(fileIn, source)


def test_oxld():
    fileIn = r'D:\work\database\dict\牛津高阶英汉双解词典（第9版）.mdx'
    source = "oxld-9"
    test(fileIn, source)


if __name__ == "__main__":
    test_oxld()

    print("{} tags writing...".format(len(tagSets)))
    with open("./output/tag_set1.txt", "w") as f:
        for i in sorted(tagSets):
            f.write(i + "\n")
