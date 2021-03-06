import requests
import json
import lxml
from lxml import etree
import re
import os


class XiaozhanCrawler(object):

    def __init__(self):
        self.source = "xiaozhan"
        self.url = "http://top.zhan.com/cihui/%s-%s.html"
        self.countryCh2En = {"美": "US", "英": "UK"}
        self.inflectionCh2En = {"复数": "", "过去式": "", "过去分词": "", "现在分词": "", "第三人称单数": ""}
        self.items = ["PhoneticSymbols", "ParaPhrases", "Inflections", "Collocations", "Derivatives"]
        self.dictPath = "./output/dict/xiaozhan/"
        if not os.path.exists(self.dictPath):
            os.makedirs(self.dictPath)

    def get_infos(self, lexicon):
        """
        提取词汇信息.
        """
        lexicon = lexicon.strip()
        if lexicon in os.listdir(self.dictPath):
            return self.read_infos(lexicon)
        else:
            url = self.url % ("ielts", lexicon)
            response = requests.get(url)
            html = etree.parse(url, etree.HTMLParser(encoding="utf-8"))
            if len(lexicon.split()) > 1:
                lexiconType = "Phrase"
            else:
                lexiconType = "Word"
            result = {"Lexicon": lexicon, "type": lexiconType}
            for k in self.items:
                try:
                    if k == "PhoneticSymbols":
                        result[k] = eval("self.get_%s(lexicon)" % k)
                    elif k == "Derivatives":
                        id = html.xpath("//body")[0].attrib["data-word_id"]
                        result[k] = eval("self.get_%s(id, lexicon)" % k)
                    else:
                        result[k] = eval("self.get_%s(html)" % k)
                except Exception as e:
                    print("Error: {}, {}".format(lexicon, repr(e)))
            # 保存词汇信息
            if not (lexicon in result["Inflections"].values()):
                isSave = False
                for k in self.items:
                    if k in result.keys() and result[k]:
                        isSave = True
                        break
                if isSave:
                    self.save_infos(lexicon, result)
            else:
                print("Warning: {} in Inflections: {}".format(lexicon, result["Inflections"]))
            return result

    def get_phonetic_symbol(self, html):
        """
        音标提取.
        """

        ps = html.xpath("//div[@class='cssVocWordVideo jsControlAudio']/span")
        outs = []
        if len(ps) >= 2:
            country = ps[0].text
            name = "/" + ps[1].text[1:-1] + "/"
            out = {"country": self.countryCh2En[country], "audioUrl": "", "name": name, "source": self.source}
            outs.append(out)
        return outs

    def get_PhoneticSymbols(self, lexicon):
        """
        美英音标提取.
        """
        outs = []
        # IELTS
        url = self.url % ("ielts", lexicon)
        html = etree.parse(url, etree.HTMLParser(encoding="utf-8"))
        outs += self.get_phonetic_symbol(html)

        # TOEFL
        url = self.url % ("toefl", lexicon)
        html = etree.parse(url, etree.HTMLParser(encoding="utf-8"))
        outs += self.get_phonetic_symbol(html)

        return outs

    def get_ParaPhrases(self, html, name="toefl"):
        """
        释义、例句信息提取.
        """
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
                    sentences += [{"english": e, "chinese": c, "source": self.source + "-jianming", "audioUrlUS": "",
                                   "audioUrlUK": ""}
                                  for e, c in zip(jianmingSentEns, jianmingSentChs)]
                if len(sceneSentEns) == len(sceneSentChs):
                    sentences += [{"english": e, "chinese": c, "source": self.source + "-scene", "audioUrlUS": "",
                                   "audioUrlUK": ""}
                                  for e, c in zip(sceneSentEns, sceneSentChs)]
                if len(toeflSentEns) == len(toeflSentChs):
                    sentences += [{"english": e, "chinese": c, "source": self.source + "-" + name, "audioUrlUS": "",
                                   "audioUrlUK": ""}
                                  for e, c in zip(toeflSentEns, toeflSentChs)]
                paraphrase = {"pos": pos, "english": "", "chinese": parapch, "Sentences": sentences,
                              "source": self.source}

                paraphrases.append(paraphrase)
            except Exception as e:
                print("Error: {}".format(repr(e)))
                pass
        return paraphrases

    def get_Inflections(self, html):
        """
        变形词提取.
        """
        words = html.xpath("//ul[@class='cssVocForMatVaried']/li/text()")
        names = html.xpath("//ul[@class='cssVocForMatVaried']/li/span/text()")
        assert len(words) == len(names)
        out = {}
        for w, n in zip(words, names):
            out[n] = w.strip()
        return out

    def get_fixed_collocations(self, html):
        """
        固定搭配提取.
        """
        result = html.xpath("//li[@class='cssVocContTwo jsVocContTwo  active']/ul/li")
        outs = []
        for r in result:
            collection = r.xpath("./div/p[@class='cssVocTotoleChinese']/text()")[0].strip()
            ch = r.xpath("./div/p[@class='cssVocTotoleEng']/text()")[0].strip()
            outs.append({"name": collection, "chinese": ch, "source": self.source})
        return outs

    def get_idiomatic_usage(self, html):
        """
        习惯用法提取.
        """
        result = html.xpath("//ul[@class='cssVocContTogole jsVocContTogole']")
        outs = []
        for r in result:
            usage = r.xpath("./div/p[@class='cssVocTotoleChinese']/text()")
            ch = r.xpath("./div/p[@class='cssVocTotoleEng']/text()")[0].strip()
            outs.append({"idiomatic_usage": usage, "chinese": ch, "source": self.source})
        return outs

    def get_Collocations(self, html):
        """
        搭配提取.
        """
        # 固定搭配
        outs = self.get_fixed_collocations(html)
        # 习惯用法
        # outs += self.get_idiomatic_usage(html)
        return outs

    def get_Derivatives(self, id, lexicon):
        """
        派生词提取.
        """
        outs = []
        html = etree.parse(f"http://top.zhan.com/vocab/detail/one-2-ten.html?test_type=2&word_id={id}&word={lexicon}",
                           etree.HTMLParser(encoding="utf-8"))
        ens = html.xpath("//p[@class='cssDeriWordsBoxId']/text()")
        chs = html.xpath("//ul[@class='cssDeriWordsBoxType']/li/text()")
        assert len(ens) == len(chs)
        for en, ch in zip(ens, chs):
            para = ch.split(".", 1)
            if len(para) != 2:
                continue
            pos = para[0].strip() + "."
            parapch = para[1].strip()
            outs.append({"Lexicon": en.strip(), "chinese": parapch, "pos": pos, "source": self.source})
        return outs

    def save_infos(self, lexicon, infos):
        """
        保存词汇信息.
        """
        with open(self.dictPath + str(lexicon), "w", encoding="utf-8") as f:
            json.dump(infos, f, ensure_ascii=False)

    def read_infos(self, lexicon):
        """
        读取词汇信息.
        """
        with open(self.dictPath + str(lexicon), "r", encoding="utf-8") as f:
            return json.load(f)


if __name__ == "__main__":
    c = XiaozhanCrawler()
    import pandas as pd
    from multiprocessing import Pool

    c.get_infos("taste")

    # words = pd.read_csv(r"D:\work\database\单词-缺失美英音标-汇总2-sorted.csv", header=None)
    # print("words shape={}".format(words.shape))
    #
    # p = Pool(1)
    # words = words[0].values
    # for i in range(len(words)):
    #     p.apply(c.get_infos, (words[i],))
