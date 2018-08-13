from Browser import Clova_News
from multiprocessing import cpu_count, Process, Queue, Array
import pandas as pd
import pickle
from .config import *


if __name__ == 'bot.__init__':
    in_queue = Queue()
    out_queues = [Queue() for i in range(MULTIPROCESSOR_NUM)]
    flags = Array('i', MULTIPROCESSOR_NUM)
    print('{}개의 셀레니움을 시작 중입니다.'.format(MULTIPROCESSOR_NUM))
    chromes = [Process(target=Clova_News, args=(in_queue, out_queues, i)) for i in range(MULTIPROCESSOR_NUM)]
    [c.start() for c in chromes]
    symbol_dict = pd.read_csv('symbols.csv', index_col='Name', dtype=str).to_dict()['Code']
    try:
        with open('./interest_list.pickle', 'rb') as pic:
            interest_list = pickle.load(pic)
    except:
        print("관심종목 리스트가 없어 새로운 dict을 생성합니다.")
        interest_list = {}