import requests
import json
import lxml
from lxml import etree
import re

word = "book"
url = f"http://top.zhan.com/cihui/toefl-{word}.html"

response = requests.get(url)
x = response.text.encode(response.encoding).decode("utf-8")
html = etree.parse(url, etree.HTMLParser(encoding="utf-8"))


# result = etree.tostring(html).decode("utf-8")

def get_paraphrases(html):
    ps = html.xpath("//li[@class='cssVocCont jsVocCont active']/ul/li")
    paraphrases = []
    for p in ps:
        try:
            # 获取词性、释义信息
            paras = p.xpath("./div/p[@class='cssVocTotoleChinese']/text()")[0]
            para = paras.split(".", 1)
            if len(para) != 2:
                continue
            pos = para[0] + "."
            parapch = para[1].strip()

            # 获取简明例句
            sentInfos = p.xpath("./div/div/div[1]/descendant::p[@class='cssVocExEnglish']")
            jianmingSentEns = [i.xpath('string(.)').strip() for i in sentInfos]
            sentInfos = p.xpath("./div/div/div[1]/descendant::p[@class='cssVocExChinese']")
            jianmingSentChs = [i.xpath('string(.)').strip() for i in sentInfos]

            # 获取情景例句
            sentInfos = p.xpath("./div/div/div[2]/descendant::p[@class='cssVocExEnglish']")
            sceneSentEns = [i.xpath('string(.)').strip() for i in sentInfos]
            sentInfos = p.xpath("./div/div/div[2]/descendant::p[@class='cssVocExChinese']")
            sceneSentChs = [i.xpath('string(.)').strip() for i in sentInfos]

            # 获取托福考试例句
            sentInfos = p.xpath("./div/div/div[3]/descendant::p[@class='cssVocExEnglish']")
            toeflSentEns = [i.xpath('string(.)').strip() for i in sentInfos]
            sentInfos = p.xpath("./div/div/div[3]/descendant::p[@class='cssVocExChinese']")
            toeflSentChs = [i.xpath('string(.)').strip() for i in sentInfos]

            # 添加例句
            sentences = []
            if len(jianmingSentEns) == len(jianmingSentChs):
                sentences += [{"english": e, "chinese": c, "source": "jianming", "audioUrlUS": "", "audioUrlUK": ""} for
                              e, c in zip(jianmingSentEns, jianmingSentChs)]
            if len(sceneSentEns) == len(sceneSentChs):
                sentences += [{"english": e, "chinese": c, "source": "scene", "audioUrlUS": "", "audioUrlUK": ""} for
                              e, c in zip(sceneSentEns, sceneSentChs)]
            if len(toeflSentEns) == len(toeflSentChs):
                sentences += [{"english": e, "chinese": c, "source": "toefl", "audioUrlUS": "", "audioUrlUK": ""} for
                              e, c in zip(toeflSentEns, toeflSentChs)]
            paraphrase = {"pos": pos, "english": "", "chinese": parapch, "Sentences": sentences, "source": "xiaozhan"}

            paraphrases.append(paraphrase)
        except Exception as e:
            print(repr(e))
            pass
    return paraphrases


get_paraphrases(html)
