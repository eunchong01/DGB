from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import pickle
import pandas as pd
from Browser import Clova_News
from .__init__ import in_queue, out_queues, symbol_dict, chromes, flags, interest_list
from multiprocessing import Queue, Process, cpu_count, Array
from .config import *

def news_pretty_response(name, df):
    df.reset_index(inplace = True)
    response = name + " 뉴스를 요약해줄게요" + '\n' + '\n'
    for idx in df.index:
        response += "▶"+str(idx+1)+"번 뉴스 : " + df.loc[idx, 'title'] + '\n'
        response += "「"
        response += df.loc[idx, 'summary']
        response += "」"  + '\n\n'
    return response

def recommend_pretty_response(l):
    if len(l) == 0:
        return '최근 3일 동안 신규 추천 종목이 없어요. 내일을 기다려봐요'
    response = '최근 3일 동안 여러 증권사에서 가장 많은 추천을 받은 다섯 종목을 알려줄게요!' + '\n' + '\n'
    response += "「"
    for ix, code in enumerate(l):
        name = [key for key, value in symbol_dict.items() if value == code][0]
        if ix != len(l)-1:
            response += name + ', '
        else:
            response += name
    response += "」"
    return response

def stock_summary_pretty_response(name, l, filing=True):
    response = "「"+name+"」" + " 관련해서 요약해줄게요" + '\n'
    response += "▶"+'현재가 : ' + l[0][0]  + '\n'
    if l[0][2][0:1] == '-':
        response += "▶"+'등락폭 : -' + l[0][1] + ' (흑흑) \n'
    else:
        response += "▶"+'등락폭 : +' + l[0][1] + ' (하하) \n'
    response += "▶"+'등락률 : ' + l[0][2] + '\n'+ '\n'
    response += "▶"+l[1][0] + ' 기준 수급 (장 마감 후 갱신)' + '\n'
    response += '기관   : ' + l[1][1] + '주' + '\n'
    response += '외국인 : ' + l[1][2] + '주' + '\n' + '\n'
    if filing:
        response += "▶" + '최근 공시' + '\n'
        if len(l[3]) != 0:
            response += "-" + l[3][0][1] + ' ' + l[3][0][2]  + '\n'
            response += l[3][0][3]  + '\n'
            response += '더 많은 공시를 위해서는 ' + '\'' + name + '\' 공시 알려줘 라고 말해봐요' + '\n'
        else:
            response += name + ' 관련한 최근 일주일 간의 공시가 없어요(흑흑)' + '\n'
        response += '\n'

    response +=  "▶"+'최근 뉴스' + '\n'
    if type(l[2][0]) == int or type(l[2][0]) == float: #최근 뉴스가 없는 경우
        response += '최근 3일 동안의 뉴스가 없어요... :( \n'
    else:
        for i in range(len(l[2][0])):
            response += l[2][0][i] + '\n'
            response += l[2][1][i] + '\n' + '\n'
    response += '뉴스 세줄요약 기능이 있어요! \''+ name +  '뉴스 요약해줘\'라고 말해봐요(감동) \n\n'
    return response

def interest_list_pretty_response(l):
    if len(l) == 0:
        return '등록된 관심종목이 없어요(흑흑)'
    response = '현재 등록된 관심종목은 ' + '\n'
    response += '(별)'
    for ix, name in enumerate(l):
        if ix != len(l)-1:
            response += name + ', '
        else:
            response += name
    response += '(별)입니다'
    return response

def market_summary_pretty_response(name, l):
    response = name + ' 시장을 요약해줄게요' + '\n'
    response += "▶" + "현재 지수 : " + l[0] + '\n'
    if l[1].find("+") != -1:
        response += "▶" + "전날 대비 : +" + l[1].split(' ')[0] + ' (' + l[1].split(' ')[1] + ')' +  ' (하하) \n'
    else:
        response += "▶" + "전날 대비 : -" + l[1].split(' ')[0] + ' (' + l[1].split(' ')[1] + ')' + ' (흑흑) \n'
    response += "▶" + "수급" + '\n'
    response += "개인 : " + l[4] + '\n' + "외국인 : " + l[5] + '\n' + '기관 : ' + l[6] + '\n'
    return response

def rise_fall_pretty_response(out1, out2):
    response = '코스피, 코스닥 시장에서 가장 많이 상승, 하락한 주식 목록을 알려줄게요' + '\n'
    response += "▶" + "급등 목록" + '\n'
    for ix, stock_info in enumerate(out1):
        if ix != len(out1)-1:
            response += stock_info[0] + '(+{}%)'.format(stock_info[1]) + ", "
        else:
            response +=  stock_info[0] + '(+{}%)'.format(stock_info[1]) + '\n'
    response += "▶" + "급락 목록" + '\n'
    for ix, stock_info in enumerate(out2):
        if ix != len(out2)-1:
            response += stock_info[0] + '(-{}%)'.format(stock_info[1]) + ", "
        else:
            response +=  stock_info[0] + '(-{}%)'.format(stock_info[1]) + '\n'
    return response

def filing_pretty_response(name, l):
    if len(l) != 0:
        response = name + ' 관련한 최근 일주일 간의 공시를 알려줄게요(하하)' + '\n'
        for g in l:
            response += "▶" + g[1] + ' ' + g[2]  + '\n'
            response += g[3]  + '\n'
    else:
        response = name + ' 관련한 최근 일주일 간의 공시가 없어요(흑흑)' + '\n'

    return response


def keyboard(request):
    return JsonResponse({'type' : 'text'})

def reserving_queue():
    ix = None
    while ix == None:
        for i, v in enumerate(flags):
            if v == 0:
                flags[i] = 1
                ix = i
                break
    return ix

@csrf_exempt
def answer(request):
    json_str = (request.body).decode('utf-8')
    received_json = json.loads(json_str)
    content = received_json['content']
    user_key = received_json['user_key']

    if content.find('도움말') != -1 or content.find('사용법') != -1 or content.find('안녕') != -1:
        resp = "기능을 알려줄게요(감동)" + '\n' + '\n'
        resp += "1) 종목요약 :" + '\n' + '- 삼성전자 요약해줘, 삼성전자 주가 알려줘' + '\n'
        resp += "2) 시장요약 :" + '\n' + '- 코스피 시장 요약해줘, 코스닥 시장 요약해줘' + '\n'
        resp += "3) 뉴스요약 :" + '\n' + '- 삼성전자 뉴스 요약해줘!' + '\n'
        resp += "4) 종목추천 :" + '\n' + '- 증권사 종목 추천 알려줘~~' + '\n'
        resp += "5) 관심종목 관리 :" + '\n' + '- 삼성전자 관심종목 등록해줘, 빼줘, 알려줘' + '\n'
        resp += "6) 관심종목 일괄요약 :" + '\n' + '- 관심종목 요약해줘~' + '\n'
        resp += "7) 급등락 종목 조회 :" + '\n' + '- 오늘 많이 오른 주식 알려줘!' + '\n'
        resp += "8) 공시 조회 :" + '\n' + '- 최근 삼성전자 공시 알려줘!' + '\n'
        return JsonResponse({
            'message': {
                'text': resp
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif content.find('관심종목') != -1 and (content.find('등록') != -1 or content.find('추가') != -1 or content.find('넣') != -1):
        if user_key not in interest_list.keys():
            print("새 user_key 등록 :", user_key)
            interest_list[user_key] = []
        text_list = content.split(' ')
        name = ' '.join(text_list[0:
            [True if i.find('관심') != -1 else False for i in text_list].index(True)]).lower()
        try:
            code = symbol_dict[name]
        except:
            resp = name + '에 해당하는 종목이 없어요 :('
            return JsonResponse({
                'message': {
                    'text': resp
                },
                'keyboard': {
                    'type': 'text'
                }

            })
        if len(interest_list[user_key]) >= MAX_INTEREST_NUM:
            return JsonResponse({
                'message': {
                    'text': '관심종목은 '+MAX_INTEREST_NUM+'개까지 등록할 수 있어요 (흑흑) 중요하지 않은 종목은 관심종목에서 빼보세요!'
                },
                'keyboard': {
                    'type': 'text'
                }

            })
        #관심종목등록
        if name not in interest_list[user_key]:
            interest_list[user_key].append(name)
        with open('./interest_list.pickle', 'wb') as pic:
            pickle.dump(interest_list, pic, protocol=pickle.HIGHEST_PROTOCOL)
        resp = interest_list_pretty_response(interest_list[user_key])
        return JsonResponse({
            'message': {
                'text': resp
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif content.find('관심종목') != -1 and (content.find('제거') != -1 or content.find('취소') != -1 or content.find('빼') != -1 or content.find('제외') != -1):
        if user_key not in interest_list.keys():
            print("새 user_key 등록 :", user_key)
            interest_list[user_key] = []
        text_list = content.split(' ')
        name = ' '.join(text_list[0:
                                  [True if i.find('관심') != -1 else False for i in text_list].index(True)]).lower()
        try:
            code = symbol_dict[name]
        except:
            resp = name + '에 해당하는 종목이 없어요 :('
            return JsonResponse({
                'message': {
                    'text': resp
                },
                'keyboard': {
                    'type': 'text'
                }

            })
        #관심종목제거
        if name in interest_list[user_key]:
            interest_list[user_key].remove(name)
        with open('./interest_list.pickle', 'wb') as pic:
            pickle.dump(interest_list, pic, protocol=pickle.HIGHEST_PROTOCOL)
        resp = interest_list_pretty_response(interest_list[user_key])
        return JsonResponse({
            'message': {
                'text': resp
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif content.find('관심종목') != -1 and (content.find('요약') != -1 or content.find('뉴스') != -1):
        resp = ''
        name_list = {}
        ix = reserving_queue()
        for name in interest_list[user_key]:
            code = symbol_dict[name]
            in_queue.put(['stock_summary', [code, name], ix])
        current_len = 0
        while current_len < len(interest_list[user_key]):
            name, out = out_queues[ix].get()
            resp += stock_summary_pretty_response(name, out, filing=False)
            current_len += 1
        flags[ix] = 0

        return JsonResponse({
            'message': {
                'text': resp
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif content.find('관심종목') != -1:
        if user_key not in interest_list.keys():
            print("새 user_key 등록 :", user_key)
            interest_list[user_key] = []
        resp = interest_list_pretty_response(interest_list[user_key])
        return JsonResponse({
            'message': {
                'text': resp
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif (content.find('요약') != -1 or content.find('알') != -1 or content.find('어때') != -1) and (content.find('코스피') != -1 or content.find('코스닥') != -1 or content.find('시장') != -1):
        if content.find('코스닥') != -1:
            market = '코스닥'
        else:
            market = '코스피'
        ix = reserving_queue()
        in_queue.put(['market_summary', [market, ], ix])
        out = out_queues[ix].get()
        flags[ix] = 0
        resp = market_summary_pretty_response(market, out)
        return JsonResponse({
            'message': {
                'text': resp
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif content.find('뉴스') != -1: #뉴스요약
        text_list = content.split(' ')
        name = ' '.join(text_list[0:
                                  [True if i.find('뉴스') != -1 else False for i in text_list].index(True)]).lower()
        try:
            code = symbol_dict[name]
        except:
            resp = name + '에 해당하는 종목이 없어요 :('
            return JsonResponse({
                'message': {
                    'text': resp
                },
                'keyboard': {
                    'type': 'text'
                }

            })
        ix = reserving_queue()
        in_queue.put(['recent_news', [code, NEWS_RECENT_DAY, MAX_NEWS_SUMMARY], ix])
        news_list = out_queues[ix].get()
        if type(news_list) == str:
            resp = '최근 뉴스가 없습니다.'
        elif not type(news_list) != pd.DataFrame:
            for kk, news in news_list.iterrows():
                in_queue.put(['do_summary', [news, SUMMARY_SENTENCES], ix])
            summaries = pd.DataFrame(columns=['title', 'summary'])
            while len(summaries) < len(news_list):
                summaries = summaries.append(out_queues[ix].get())
            resp = news_pretty_response(name, summaries)
        flags[ix] = 0
        return JsonResponse({
            'message': {
                'text': resp
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif content.find('요약') != -1 or content.find('주가') != -1:
        text_list = content.split(' ')
        name = ' '.join(text_list[0:
                                  [True if i.find('요약') != -1 or i.find('주가') != -1 else False for i in text_list].index(True)]).lower()
        try:
            code = symbol_dict[name]
        except:
            resp = name + '에 해당하는 종목이 없어요 :('
            return JsonResponse({
                'message': {
                    'text': resp
                },
                'keyboard': {
                    'type': 'text'
                }

            })
        ix = reserving_queue()
        in_queue.put(['stock_summary', [code, name], ix])
        ix2 = reserving_queue()
        in_queue.put(['get_filing', [name, ], ix2])
        _, out = out_queues[ix].get()
        out.append(out_queues[ix2].get())
        resp = stock_summary_pretty_response(name, out)
        flags[ix] = 0
        flags[ix2] = 0
        return JsonResponse({
            'message': {
                'text': resp
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif content.find('등락') != -1 or content.find('오른') != -1 or content.find('내린') != -1\
            or content.find('상승') != -1 or content.find('하락') != -1 or content.find('급등') != -1\
            or content.find('급락') != -1 or content.find('떨어') != -1 :
        ix = reserving_queue()
        in_queue.put(['rise_fall', ['rise', ], ix])
        ix2 = reserving_queue()
        in_queue.put(['rise_fall', ['fall', ], ix2])
        out1 = out_queues[ix].get()
        out2 = out_queues[ix2].get()
        flags[ix] = 0
        flags[ix2] = 0
        return JsonResponse({
            'message': {
                'text': rise_fall_pretty_response(out1, out2)
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif content.find('종목') != -1 and content.find('추천') != -1:
        ix = reserving_queue()
        in_queue.put(['recommend', [1, ], ix])
        recommend_list = out_queues[ix].get()
        flags[ix] = 0
        return JsonResponse({
            'message': {
                'text': recommend_pretty_response(recommend_list)
            },
            'keyboard': {
                'type': 'text'
            }

        })

    elif content.find('공시') != -1:
        text_list = content.split(' ')
        name = ' '.join(text_list[0:
                                  [True if i.find('공시') != -1 else False for i in
                                   text_list].index(True)]).lower()
        try:
            code = symbol_dict[name]
        except:
            resp = name + '에 해당하는 종목이 없어요 :('
            return JsonResponse({
                'message': {
                    'text': resp
                },
                'keyboard': {
                    'type': 'text'
                }

            })
        ix = reserving_queue()
        in_queue.put(['get_filing', [name], ix])
        resp = out_queues[ix].get()
        flags[ix] = 0
        return JsonResponse({
            'message': {
                'text': filing_pretty_response(name, resp)
            },
            'keyboard': {
                'type': 'text'
            }

        })

    else:
        return JsonResponse({
            'message': {
                'text': '학습되지 않은 명령이에요. 사용법이 궁금하면 도움말이라고 외쳐봐요(제발)'
            },
            'keyboard': {
                'type': 'text'
            }

        })

