import collections
import datetime
import json
import math
import random
import re
import time
from collections import Counter
import numpy as np

import pandas as pd
import requests

from konlpy.tag import Mecab
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
from bot.config import *


class Clova_News():
    def __init__(self, in_queue, out_queues,i):  # ticker_path에 Ticker라는 column이 있어야함
        self.in_queue = in_queue
        self.out_queues = out_queues
        self.link = ''
        self.title = ''
        self.content = ''
        self.summary = ''
        self.dart_api = 'd74599ed29c73354a63fa01fabb53271a717545a'
        self.options = webdriver.ChromeOptions()
        self.nlp = Mecab()
        self.to_nouns = Mecab.nouns
        self.__load_stopwords()

        self.options.add_argument('headless')
        self.options.add_argument('window-size=1920x1080')
        self.options.add_argument("disable-gpu")
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')

        self.options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36")
        self.driver = webdriver.Chrome(chrome_options=self.options)
        self.news_df = pd.DataFrame(columns=['Date', 'Ticker', 'Title', 'Link']).set_index('Date')
        self.dart_df = pd.DataFrame(columns=['Date', 'Ticker', 'Category', 'Title']).set_index('Date')
        self.dart_dict = {'A001': '사업보고서', 'A002': '반기보고서', 'A003': '분기보고서', 'A004': '등록법인결산서류(자본시장법이전)',
                          'A005': '소액공모법인결산서류', 'B001': '주요사항보고서',
                          'B002': '주요경영사항신고(자본시장법', 'C001': '증권신고(지분증권)', 'C002': '증권신고(채무증권)', 'C003': '증권신고(파생결합증권)',
                          'C004': '증권신고(합병등)', 'C005': '증권신고(기타)', 'C006': '소액공모(지분증권)', 'C007': '소액공모(채무증권)',
                          'C008': '소액공모(파생결합증권)', 'C009': '소액공모(합병등)', 'C010': '소액공모(기타)', 'C011': '호가중개시스템을통한소액매출',
                          'D001': '주식등의대량보유상황보고서', 'D002': '임원ㆍ주요주주특정증권등소유상황보고서', 'D003': '의결권대리행사권유', 'D004': '공개매수',
                          'E001': '자기주식취득/처분', 'E002': '신탁계약체결/해지', 'E003': '합병등종료보고서', 'E004': '주식매수선택권부여에관한신고',
                          'E005': '사외이사에관한신고', 'E006': '주주총회소집공고', 'E007': '시장조성/안정조작', 'E008': '합병등신고서(자본시장법',
                          'F001': '감사보고서', 'F002': '연결감사보고서', 'F003': '결합감사보고서', 'F004': '회계법인사업보고서',
                          'G001': '증권신고(집합투자증권-신탁형)',
                          'G002': '증권신고(집합투자증권-회사형)', 'G003': '증권신고(집합투자증권-합병)', 'H001': '자산유동화계획/양도등록',
                          'H002': '사업/반기/분기보고서',
                          'H003': '증권신고(유동화증권등)', 'H004': '채권유동화계획/양도등록', 'H005': '수시보고', 'H006': '주요사항보고서',
                          'I001': '수시공시',
                          'I002': '공정공시', 'I003': '시장조치/안내', 'I004': '지분공시', 'I005': '증권투자회사', 'I006': '채권공시',
                          'J001': '대규모내부거래관련',
                          'J002': '대규모내부거래관련(구)', 'J004': '기업집단현황공시', 'J005': '비상장회사중요사항공시', 'J006': '기타공정위공시', }
        print('{}번째 프로세스 구동 완료'.format(i))

        while True:
            task = self.in_queue.get()
            func_name, args, self.ix = task[0], task[1], task[2]
            getattr(self, func_name)(*args)

    def set_tickers(self, tickers):
        self.tickers = tickers

    def recommend(self, __):
        from collections import Counter
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        sdate = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime('%Y-%m-%d')
        i = 1
        break_signal = False
        buys = []
        while not break_signal:
            self.driver.get('http://hkconsensus.hankyung.com/apps.analysis/analysis.list?skinType=business&sdate={}&edate={}&pagenum=80&order_type=&now_page={}'.format(sdate, today, i))
            print('http://hkconsensus.hankyung.com/apps.analysis/analysis.list?skinType=business&sdate={}&edate={}&pagenum=80&order_type=&now_page={}'.format(sdate, today, i))
            WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(
                (By.XPATH, '//*/div[2]/table/thead/tr/th[2]/a')))
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            soup.findAll('td', attrs={'class': 'dv_input'})
            date = soup.findAll('td', attrs={'class': 'first txt_number'})
            if len(date) == 0:
                break_signal = True
                break
            stock_name = soup.findAll('div', attrs={'class': 'pop01 disNone'})
            opinion = soup.findAll('td')
            iContents = []
            if len(stock_name) == 0:
                return []
            for j in range(0, len(stock_name)):
                jContents = []
                jdate = date[j].text.strip()
                jstock_name = stock_name[j].text.strip().split('(')[1].split(')')[0]
                jopinion = opinion[3 + 9 * j].text.strip()

                jContents.append(jdate)
                #if pd.Timestamp(self.recommend_df.iloc[0,0]) - pd.DateOffset(days=1) >= pd.Timestamp(jdate):
                jContents.append(jstock_name)
                jContents.append(jopinion)
                iContents.append(jContents)
            result = pd.DataFrame(iContents)
            buy = result[(result[2] == "Buy") | (result[2] == "Strong Buy")]
            buys += list(buy[1].values)
            i += 1
        buys = [i[0] for i in Counter(buys).most_common(RECOMMEND_NUM)]
        self.out_queues[self.ix].put(buys)

    def stock_summary(self, *args):
        code = args[0]
        name = args[1]
        out = []
        self.driver.get('https://finance.naver.com/item/sise.nhn?code={}'.format(code))
        WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(
            (By.XPATH, '//*[@id="_rate"]/span')))
        rate = self.driver.find_element_by_xpath('//*[@id="_rate"]/span').text
        price = self.driver.find_element_by_xpath('//*[@id="_nowVal"]').text
        changes =  self.driver.find_element_by_xpath('// *[ @ id = "_diff"] / span').text
        out.append([price, changes, rate])

        self.driver.get('https://finance.naver.com/item/frgn.nhn?code={}'.format(code))
        WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(
            (By.XPATH, '//*[@id="content"]/div[2]/table[1]/tbody/tr[4]/td[6]/span')))
        date = self.driver.find_element_by_xpath('//*[@id="content"]/div[2]/table[1]/tbody/tr[4]/td[1]/span').text
        korean = self.driver.find_element_by_xpath('//*[@id="content"]/div[2]/table[1]/tbody/tr[4]/td[6]/span').text
        foreign = self.driver.find_element_by_xpath('//*[@id="content"]/div[2]/table[1]/tbody/tr[4]/td[7]/span').text
        out.append([date, korean, foreign])
        df = self.get_news(code, NEWS_RECENT_DAY, MAX_NEWS_SUMMARY)
        if type(df) == str:
            out.append([-1, -1])
        else:
            out.append([df['Title'].values, df['Link'].values])
        self.out_queues[self.ix].put([name, out])

    def market_summary(self, *args):
        market = args[0]
        if market == '코스닥':
            self.driver.get('https://finance.naver.com/sise/sise_index.nhn?code=KOSDAQ')
        else:
            self.driver.get('https://finance.naver.com/sise/sise_index.nhn?code=KOSPI')
        WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(
            (By.XPATH, '//*[@id="now_value"]')))
        index = self.driver.find_element_by_xpath('//*[@id="now_value"]').text
        change_rate = self.driver.find_element_by_xpath('//*[@id="change_value_and_rate"]').text
        up = self.driver.find_element_by_xpath('//*[@id="contentarea_left"]/div[2]/div/div[2]/table/tbody/tr[4]/td/ul/li[2]/a/span').text
        down = self.driver.find_element_by_xpath('//*[@id="contentarea_left"]/div[2]/div/div[2]/table/tbody/tr[4]/td/ul/li[4]/a/span').text
        indiv = self.driver.find_element_by_xpath('//*[@id="contentarea_left"]/div[2]/div/dl/dd[1]/span').text
        foreign = self.driver.find_element_by_xpath('//*[@id="contentarea_left"]/div[2]/div/dl/dd[2]/span').text
        korean = self.driver.find_element_by_xpath('//*[@id="contentarea_left"]/div[2]/div/dl/dd[3]/span').text

        out = [index, change_rate, up, down, indiv, foreign, korean]

        self.out_queues[self.ix].put(out)

    def recent_news(self, *args):
        ticker = args[0]
        recent_day = args[1]
        max_num = args[2]
        temps = []
        p = 1
        num = 0
        while True:
            print('https://finance.naver.com/item/news_news.nhn?code={}&page={}'.format(ticker, p))
            url = 'https://finance.naver.com/item/news_news.nhn?code={}&page={}'.format(ticker, p)
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(
                (By.XPATH, '//*/div[1]/table[1]/tbody/tr[1]/td[1]/a')))
            trs = self.driver.find_elements_by_xpath("/html/body/div/table[1]/tbody[1]/*")

            for tr in trs:
                try:
                    title = tr.find_element_by_class_name('title').text
                except:
                    self.out_queues[self.ix].put(None)
                    return
                if tr.get_attribute('class').startswith('relation_lst') or \
                        title.startswith('[한경로보') or \
                        title.startswith('[스팟') or \
                        title.startswith('[이데일리N') or \
                        title.startswith('[마켓포인') or \
                        title.startswith('[표]') or \
                        title.startswith('[fnRAS') or \
                        title.startswith('<코>'):
                    continue
                date = tr.find_element_by_class_name('date').text
                if pd.Timestamp(date) <= (
                pd.Timestamp(datetime.datetime.now() - pd.DateOffset(days=recent_day,
                                                                        hours=int(time.strftime("%H"))))):

                    self.out_queues[self.ix].put(pd.concat(temps) if len(temps) != 0 else '뉴스가 없습니다.')
                    return
                link = tr.find_element_by_tag_name('a').get_attribute("href")

                if len(tr.find_elements_by_class_name('title')) > 0:
                    temp = pd.DataFrame([[ticker, title, link]], columns=['Ticker', 'Title', 'Link'], index=[date])
                    temps.append(temp)

                num += 1
                if num == max_num:
                    self.out_queues[self.ix].put(pd.concat(temps) if len(temps) != 0 else None)
                    return
            p += 1
            time.sleep(random.uniform(0.02, 0.04))

    def get_news(self, *args):  # 인스턴스 데이터프레임에 Profile이라는 column을 만들고, 해당 칼럼에 Ticker에 해당하는 Profile을 저장함
        ticker = args[0]
        recent_day = args[1]
        max_num = args[2]
        temps = []
        p = 1
        num = 0
        while True:
            print('https://finance.naver.com/item/news_news.nhn?code={}&page={}'.format(ticker, p))
            url = 'https://finance.naver.com/item/news_news.nhn?code={}&page={}'.format(ticker, p)
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(
                (By.XPATH, '//*/div[1]/table[1]/tbody/tr[1]/td[1]/a')))
            trs = self.driver.find_elements_by_xpath("/html/body/div/table[1]/tbody[1]/*")

            for tr in trs:
                try:
                    title = tr.find_element_by_class_name('title').text
                except:
                    return '최근뉴스가 없습니다.'
                if tr.get_attribute('class').startswith('relation_lst') or \
                        title.startswith('[한경로보') or \
                        title.startswith('[스팟') or \
                        title.startswith('[이데일리N') or \
                        title.startswith('[마켓포인') or \
                        title.startswith('[표]') or \
                        title.startswith('[fnRAS') or \
                        title.startswith('<코>'):
                    continue
                date = tr.find_element_by_class_name('date').text
                if pd.Timestamp(date) <= (
                        pd.Timestamp(datetime.datetime.utcnow() - pd.DateOffset(days=recent_day, hours=-9))):
                    if len(temps) != 0:
                        return pd.concat(temps)
                    else:
                        return '최근뉴스가 없습니다.'
                link = tr.find_element_by_tag_name('a').get_attribute("href")

                if len(tr.find_elements_by_class_name('title')) > 0:
                    temp = pd.DataFrame([[ticker, title, link]], columns=['Ticker', 'Title', 'Link'], index=[date])
                    temps.append(temp)

                num += 1
                if num == max_num:
                    if len(temps) != 0:
                        return pd.concat(temps)
            p += 1
            time.sleep(random.uniform(0.02, 0.04))

    def rise_fall(self, *args):
        direction = args[0]
        Contents = []
        for i in range(2):
            base_url = "https://finance.naver.com/sise/sise_{}.nhn?sosok={}".format(direction, i)
            self.driver.get(base_url)
            for i in range(1, 10):
                contents = []
                try:
                    xpath = self.driver.find_element_by_xpath(
                        '//*[@id="contentarea"]/div[3]/table/tbody/tr[' + str(i + 2) + ']/td[2]/*')
                    kospi = xpath.text
                    xpath = self.driver.find_element_by_xpath(
                        '//*[@id="contentarea"]/div[3]/table/tbody/tr[' + str(i + 2) + ']/td[5]/*')
                    rf = xpath.text
                    Contents.append([kospi, float(rf[1:-1])])
                except:
                    pass
        rise_fall_list = pd.DataFrame(Contents).dropna().sort_values(1, ascending=False)
        self.out_queues[self.ix].put(list(rise_fall_list.values))

    def get_filing(self, *args):  # 인스턴스 데이터프레임에 Profile이라는 column을 만들고, 해당 칼럼에 Ticker에 해당하는 Profile을 저장함
        name = args[0]
        out = []
        url = 'https://dart.fss.or.kr/html/search/SearchCompany_M2.html?textCrpNM=' + name
        print(url)
        try:
            self.driver.get(url)
        except:
            pass

        try:
            WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(
                (By.XPATH, '//*[@id="listContents"]/div[1]/table/tbody/tr[15]')))
            xpath = self.driver.find_element_by_xpath('//*[@id="listContents"]/div[1]/table/tbody')
            trs = xpath.find_elements_by_tag_name('tr')
            for tr in trs:
                tds = tr.find_elements_by_tag_name('td')
                if not pd.Timestamp(tds[4].text) <= (
                        pd.Timestamp(datetime.datetime.now() - pd.DateOffset(days=FILING_RECENT_DAY,
                                                                             hours=int(time.strftime("%H"))))):
                    out.append([name, tds[4].text, tds[2].text, str(tds[2].find_element_by_tag_name('a').get_attribute("href"))])
        except:
            print("error on :", name)
        self.out_queues[self.ix].put(out)

    def get_filing2(self, *args):  # 인스턴스 데이터프레임에 Profile이라는 column을 만들고, 해당 칼럼에 Ticker에 해당하는 Profile을 저장함
        name = args[0]
        out = []
        url = 'https://dart.fss.or.kr/html/search/SearchCompany_M2.html?textCrpNM=' + name
        print(url)
        try:
            self.driver.get(url)
        except:
            pass
        try:
            WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(
                (By.XPATH, '//*[@id="listContents"]/div[1]/table/tbody/tr[15]')))
            xpath = self.driver.find_element_by_xpath('//*[@id="listContents"]/div[1]/table/tbody')
            trs = xpath.find_elements_by_tag_name('tr')
            for tr in trs:
                tds = tr.find_elements_by_tag_name('td')
                if not pd.Timestamp(tds[4].text) <= (
                        pd.Timestamp(datetime.datetime.now() - pd.DateOffset(days=FILING_RECENT_DAY,
                                                                             hours=int(time.strftime("%H"))))):
                    out.append([name, tds[4].text, tds[2].text, str(tds[2].find_element_by_tag_name('a').get_attribute("href"))])
                    return out
        except:
            print("error on :", name)

        return out


    def get_filing_api(self, start_date=(datetime.date.today() - datetime.timedelta(1)).strftime('%Y%m%d')):
        for i, ticker in enumerate(self.tickers):
            for p, key in enumerate(self.dart_dict):
                url = "http://dart.fss.or.kr/api/search.json?auth=" + self.dart_api + "&crp_cd=" + ticker + '&start_dt=' + start_date + "&bsn_tp={}".format(
                    key)
                for tr in json.loads(requests.get(url).text)['list']:
                    temp = pd.DataFrame([[tr['crp_cd'], self.dart_dict[key], tr['rpt_nm']]],
                                        columns=['Ticker', 'Category', 'Title'], index=[tr['rcp_dt']])
                    self.dart_df = self.dart_df.append(temp)
                    print("Date:", tr['rcp_dt'], end='  ')
                    print('Title : {0}    Category : {1}'.format(tr['rpt_nm'], self.dart_dict[key]))
                print(str((p + len(self.dart_dict) * i * 100) / (len(self.tickers) * len(self.dart_dict))) + "%",
                      "done")

    def read_news(self):
        # self.driver.execute_script("return document.readyState").equal('complete')
        # self.driver.get('about:blank')
        self.driver.get(self.link)
        WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(
            (By.XPATH, '//*[@id="content"]/div[2]/table/tbody/tr[1]/th/strong')))
        xpath = self.driver.find_element_by_xpath('//*[@id="content"]/div[2]/table/tbody/tr[1]/th/strong')
        self.title = xpath.text
        xpath = self.driver.find_element_by_xpath('//*[@id="news_read"]')
        self.content = xpath.text
        self.summary = ''

        children = xpath.find_elements_by_xpath('.//child::*')
        for obj in children:
            if obj.get_attribute('href') != None:
                self.content = self.content.replace(obj.text, "")
            if obj.get_attribute('class') in ['paging_wrp', 'ends_btn', 'ct_box ad_cont_wrap', 'media_end_linked',
                                              'media_end_linked_title_desc', 'media_end_linked_title',
                                              'media_end_linke_item']:
                self.content = self.content.replace(obj.text, "")
        self.content.replace('[]', '')

    def read_news2(self):
        soup = BeautifulSoup(requests.get(self.link).content, 'lxml')
        self.title = soup.find('strong', {'class': 'c p15'}).text
        soup = soup.find('div', {'id': 'news_read'})
        news_text = soup.text
        try:
            exception = soup.find('strong').text
        except:
            exception = None
        for red in soup.findChildren():
            if not red.text == exception:
                news_text = news_text.replace(red.text, '')
        news_text = news_text.replace('[]', '')
        self.content = news_text
        self.summary = ''

    def count_words(self, *args):
        news = args[0]
        self.link = news['Link']
        self.read_news()
        news_concat = self.title +'.' + self.content
        words = self.to_nouns(news_concat)
        words_dict = {word:0 for word in words}
        for word in words_dict:
            words_dict[word] = news_concat.count(word)
        return words_dict


    def do_summary(self, *args):
        news = args[0]
        summary_num = args[1]
        self.link = news['Link']
        self.read_news()
        self.summarize(num=summary_num)
        self.out_queues[self.ix].put(pd.DataFrame([[self.title, self.summary]], columns=['title', 'summary']))

    def summarize(self, num=3, select_list=SELECT_LIST):
        print(self.link)
        morphs = np.array(self.nlp.pos(self.title))
        filter_func = lambda t: True if (t[1] in select_list) and len(t[0]) >= 2 else False
        remain_index = np.array([filter_func(x) for x in morphs])
        morphs = morphs[remain_index]
        morphs = list(map(lambda t: t[0], morphs))
        sentences = self.__split_sentences('. ', '? ', '! ', '\n', '.\n', ';', )(self.content)

        dic = {}
        sentence_keys = []

        for i, sentence in enumerate(sentences):
            score = 0
            for morph in morphs:
                if sentence.find(morph) >= 0 and (sentence[-1]=="다"):
                    score += 1
            if len(sentence) != 0:
                if sentence.find('"') >= 0 and sentence[-1]=="다":
                    score += 1
            dic[i] = score
            if sentence == self.title:
                dic[i] = 0

        dic = collections.OrderedDict(sorted(dic.items(), key=lambda t: t[1], reverse=True))

        for key in dic.keys():
            if num == 0:
                break
            else:
                sentence_keys.append(key)
                num -= 1

        sentence_keys = sorted(sentence_keys)

        # print("Title :", self.title)
        for key in sentence_keys:
            self.summary += sentences[key] + ". "

    def summarize2(self):
        print(self.link)
        temp_summaries = []
        sentences = self.__split_sentences('. ', '? ', '! ', '\n', '.\n', ';', )(self.content)
        keys = self.__keywords()
        title_words = self.__split_words(self.title)
        ranks = self.__score(sentences, title_words, keys).most_common(3)
        for rank in ranks:
            temp_summaries.append(rank[0])
        temp_summaries.sort(key=lambda summary: summary[0])
        self.summary = '. '.join([summary[1] for summary in temp_summaries]) + '.'

    def __split_sentences(self, *delimiters):
        return lambda value: re.split('|'.join([re.escape(delimiter) for delimiter in delimiters]), value)

    def __split_words(self, sentence):
        """Split a string into array of words
        """
        try:
            sentence = re.sub(r'[^\w ]', '', sentence)  # strip special chars
            return [x.strip('.').lower() for x in sentence.split()]
        except TypeError:
            return None

    def __load_stopwords(self):
        with open('./stopwords.txt', encoding='utf-8') as f:
            self.stopwords = set()
            self.stopwords.update(set([w.strip() for w in f.readlines()]))

    def __keywords(self):
        NUM_KEYWORDS = 10
        text = self.__split_words(self.content)
        # of words before removing blacklist words
        if text:
            num_words = len(text)
            text = [x for x in text if x not in self.stopwords]
            freq = {}
            for word in text:
                if word in freq:
                    freq[word] += 1
                else:
                    freq[word] = 1

            min_size = min(NUM_KEYWORDS, len(freq))
            keywords = sorted(freq.items(),
                              key=lambda x: (x[1], x[0]),
                              reverse=True)
            keywords = keywords[:min_size]
            keywords = dict((x, y) for x, y in keywords)

            for k in keywords:
                articleScore = keywords[k] * 1.0 / max(num_words, 1)
                keywords[k] = articleScore * 1.5 + 1
            return dict(keywords)
        else:
            return dict()

    def __title_score(self, title, sentence):
        if title:
            title = [x for x in title if x not in self.stopwords]
            count = 0.0
            for word in sentence:
                if (word not in self.stopwords and word in title):
                    count += 1.0
            return count / max(len(title), 1)
        else:
            return 0

    def __sentence_position(self, i, size):
        normalized = i * 1.0 / size
        if (normalized > 1.0):
            return 0
        elif (normalized > 0.9):
            return 0.15
        elif (normalized > 0.8):
            return 0.04
        elif (normalized > 0.7):
            return 0.04
        elif (normalized > 0.6):
            return 0.06
        elif (normalized > 0.5):
            return 0.04
        elif (normalized > 0.4):
            return 0.05
        elif (normalized > 0.3):
            return 0.08
        elif (normalized > 0.2):
            return 0.14
        elif (normalized > 0.1):
            return 0.23
        elif (normalized > 0):
            return 0.17
        else:
            return 0

    def __length_score(self, sentence_len):
        return 1 - math.fabs(20 - sentence_len) / 20

    def __sbs(self, words, keywords):
        score = 0.0
        if (len(words) == 0):
            return 0
        for word in words:
            if word in keywords:
                score += keywords[word]
        return (1.0 / math.fabs(len(words)) * score) / 10.0

    def __dbs(self, words, keywords):
        if (len(words) == 0):
            return 0
        summ = 0
        first = []
        second = []

        for i, word in enumerate(words):
            if word in keywords:
                score = keywords[word]
                if first == []:
                    first = [i, score]
                else:
                    second = first
                    first = [i, score]
                    dif = first[0] - second[0]
                    summ += (first[1] * second[1]) / (dif ** 2)
        # Number of intersections
        k = len(set(keywords.keys()).intersection(set(words))) + 1
        return (1 / (k * (k + 1.0)) * summ)

    def __score(self, sentences, title_words, keywords):
        senSize = len(self.content)
        ranks = Counter()
        for i, s in enumerate(sentences):
            sentence = self.__split_words(s)
            titleFeature = self.__title_score(title_words, sentence)
            sentenceLength = self.__length_score(len(sentence))
            sentencePosition = self.__sentence_position(i + 1, senSize)
            sbsFeature = self.__sbs(sentence, keywords)
            dbsFeature = self.__dbs(sentence, keywords)
            frequency = (sbsFeature + dbsFeature) / 2.0 * 10.0
            # Weighted average of scores from four categories
            totalScore = (titleFeature * 1.5 + frequency * 2.0 +
                          sentenceLength * 1.0 + sentencePosition * 1.0) / 4.0
            ranks[(i, s)] = totalScore
        return ranks

    def __del__(self):
        self.driver.close()


if __name__ == '__main__':
    from multiprocessing import Queue
    inque= Queue()
    inque.put(['recommend', [None], None])
    news = Clova_News(inque, None, None)

    #news.recommend()
    # news.summary_all(news.recent_news('000660'))
    # summaries = pd.DataFrame(columns=['title', 'summary'])
    # links = news.recent_news('000880')
    #
    # for i in range(len(links)):
    #     news.link = links['Link'][i]
    #     news.read_news2()
    #     a = time.time()
    #     news.summarize()
    #     print(time.time() - a)
    #     print(news.summary)
    #     summaries = summaries.append(pd.DataFrame([[news.title, news.summary]], columns=['title', 'summary']))
    # print(summaries)
    # news.get_news(max_page=10)
    # news.df.to_csv('./news.csv')
    # news.get_filing_api()
    # print(news.dart_df)

    # reuter.export_to_csv('out.csv', encoding_type='utf-8')
