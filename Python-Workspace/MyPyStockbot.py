import asyncio
import requests
import json
import time
import pymysql
import threading
import pandas as pd

from datetime import datetime
from pytz import timezone
from apscheduler.schedulers.background import BackgroundScheduler

import yfinance as yf

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, MessageHandler, CommandHandler, CallbackQueryHandler, ApplicationBuilder, ContextTypes
from telegram.constants import ChatAction


# 텔레그램 정보
s_token = 'token_value'    # 챗봇 토큰 값
admin_id = 'admin_chat_id' # 에러메세지들을 받을 관리자 Chat ID 입력

# MySQL DB 정보
s_host = 'host'
s_port = 'port'
s_user = 'user_id'
s_pass = 'password'
s_db = 'db_name'
s_char = 'utf8'

class etf_alert_worker(threading.Thread):
    """ ETF 저가 알림 관련 worker class"""
    def __init__(self, name):
        super().__init__()
        self.name = name

    def run(self):
        tz = timezone('Asia/Seoul')
        
        sched = BackgroundScheduler()
        sched.add_job(send_low_var, 'cron', day_of_week='mon-fri', hour='9-15', minute='*/5', timezone=tz) # 알림 시간 설정
        sched.start()

async def bot_send_msg(p_text, p_chat_id):
    """ 텔레그램 메세지 전송 함수 """
    bot = telegram.Bot(s_token)
    async with bot:
        await bot.send_message(text=p_text, chat_id=p_chat_id)

async def bot_send_img(p_path, p_chat_id):
    """ 텔레그램 이미지 전송 함수 """
    bot = telegram.Bot(s_token)
    async with bot:
        await bot.send_photo(chat_id=p_chat_id, photo=open(p_path, 'rb'))

async def send_msg(message, alarm_type):
    """ user_id별 알림 on/off 정보를 불러와 메시지를 보낸다."""

    try:
        conn = pymysql.connect(host=s_host, port=s_port, user=s_user, password=s_pass, db=s_db, charset=s_char)
        cur = conn.cursor()

        sql = "SELECT * FROM user_info WHERE " + alarm_type + " = 1"

        cur.execute(sql)

        while(True):
            row = cur.fetchone()

            if row == None:
                break
            
            await dbgout_individual(message, row[0])

    except Exception as ex:
        await dbgout("send_msg() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

    finally:
        conn.close()

async def dbgout_individual(message, user_id):
    """인자로 받은 문자열을 파이썬 셸과 텔레그램으로 동시에 출력한다 : 개별 사용자 메세지 전송용"""
    print(datetime.now().strftime('[%m/%d %H:%M:%S]'), message)
    await bot_send_msg(message, user_id)

async def dbgout(message):
    """인자로 받은 문자열을 파이썬 셸과 텔레그램으로 동시에 출력한다 : 관리자 에러메세지 송신용"""
    print(datetime.now().strftime('[%m/%d %H:%M:%S]'), message)
    await bot_send_msg(message, admin_id)

async def get_ft_data(code):
    """ 현재가, 52주 고점, 평균, 52주 저점 """
    try:
        info_data = yf.Ticker(code).info
        p_info_data = yf.download(code, period='1d')

        current_price = round(p_info_data.iloc[-1]['Close'], 2)
        high_price = round(info_data['fiftyTwoWeekHigh'], 2)
        low_price = round(info_data['fiftyTwoWeekLow'], 2)
        avg_price = round((high_price + low_price) / 2, 2)

        return current_price, high_price, avg_price, low_price
        
    except Exception as ex:
        await dbgout("get_ft_data("+ str(code) + ") -> 함수 예외 발생! [내역 : " + str(ex) + "]")
        return 0, 0, 0, 0

async def get_idx_data(code):
    """인덱스 Prev Close, Current"""
    try:
        
        p_info_data = yf.download(code, period='2d')

        prevclose = round(p_info_data.iloc[-2]['Close'], 2)
        curclose = round(p_info_data.iloc[-1]['Close'], 2)

        return prevclose, curclose
        
    except Exception as ex:
        await dbgout("get_idx_data("+ str(code) + ") -> 함수 예외 발생! [내역 : " + str(ex) + "]")
        return 0, 0

async def send_exchange_info(user_id):
    """달러 정보 메시지 전송"""
    try:
        # 1. 현재환율, 52주 DATA(고가, 평균, 저가) 구하기
        current, high, avg, low = await get_ft_data('KRW=X')

        # 환율 적절성 판단
        p_or_f = ""
        if avg > current:
            p_or_f = " (O)"
        else:
            p_or_f = " (X)"
        
        total_msg = "1. 원달러 환율\n"
        total_msg = total_msg + " 52주 고점 : " + str(high) + "\n"
        total_msg = total_msg + " 52주 평균 : " + str(avg) + "\n"
        total_msg = total_msg + " 52주 저점 : " + str(low) + "\n"
        total_msg = total_msg + " 현재가 : " + str(current) + p_or_f

        # 2. 달러 인덱스의 현재가 52주 고가, 평균, 저가 구하기
        current_i, high_i, avg_i, low_i = await get_ft_data('DX-Y.NYB')

        # 환율 적절성 판단
        p_or_f_i = ""
        if avg_i > current_i:
            p_or_f_i = " (O)"
        else:
            p_or_f_i = " (X)"
        
        total_msg = total_msg + "\n\n2. 달러 인덱스\n"
        total_msg = total_msg + " 52주 고점 : " + str(high_i) + "\n"
        total_msg = total_msg + " 52주 평균 : " + str(avg_i) + "\n"
        total_msg = total_msg + " 52주 저점 : " + str(low_i) + "\n"
        total_msg = total_msg + " 현재가 : " + str(current_i) + p_or_f_i

        # 3. 달러 갭 비율 (달러지수 / 환율 X 100)
        gap_rate = round(current_i / current * 100, 2)
        avg_gap = round(avg_i / avg * 100, 2)

        # 갭 비율 적절성 판단
        p_or_f_gap = ""
        if gap_rate > avg_gap:
            p_or_f_gap = " (O)"
        else:
            p_or_f_gap = " (X)"

        total_msg = total_msg + "\n\n3. 달러 갭 비율\n"
        total_msg = total_msg + " 52주 평균 : " + str(avg_gap) + "\n"
        total_msg = total_msg + " 현재 갭 비율: " + str(gap_rate) + p_or_f_gap

        # 4. 적정 환율 (현재 달러지수 / 52주 평균 갭 비율 X 100)
        pass_rate = round(current_i / avg_gap * 100, 2)

        p_or_f_total = ""
        if pass_rate > current:
            p_or_f_total = " (O)"
        else:
            p_or_f_total = " (X)"

        total_msg = total_msg + "\n\n4. 적정 환율\n"
        total_msg = total_msg + " 적정 환율 : " + str(pass_rate) + "\n"
        total_msg = total_msg + " 현재가: " + str(current) + p_or_f_total

        if user_id != 0:
            await bot_send_msg(total_msg, user_id)
        else:
            await send_msg(total_msg, "exc_flag")

    except Exception as ex:
        await dbgout("send_exchange_info() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

async def send_idx_info(user_id):
    """ 아침 3대 지수 + 러셀2000 정보 전송 """
    try:
        # 1. 다우지수 구하기
        dow_prev_price, dow_current_price = await get_idx_data('^DJI')
        dow_gap_price = round(dow_current_price - dow_prev_price, 2)
        dow_total_percent = round((dow_current_price - dow_prev_price) / dow_prev_price * 100, 2)
        
        total_msg = "[Dow Jones]\n"
        total_msg = total_msg + " 전일 종가 : " + str(dow_prev_price) + "\n"
        total_msg = total_msg + " 금일 종가 : " + str(dow_current_price) + " / " + str(dow_gap_price) + " (" + str(dow_total_percent) + "%)"

        # 2. S&P500 지수 구하기
        snp_prev_price, snp_current_price = await get_idx_data('^GSPC')
        snp_gap_price = round(snp_current_price - snp_prev_price, 2)
        snp_total_percent = round((snp_current_price - snp_prev_price) / snp_prev_price * 100, 2)
        
        total_msg = total_msg + "\n\n[S&P 500]\n"
        total_msg = total_msg + " 전일 종가 : " + str(snp_prev_price) + "\n"
        total_msg = total_msg + " 금일 종가 : " + str(snp_current_price) + " / " + str(snp_gap_price) + " (" + str(snp_total_percent) + "%)"

        # 3. 나스닥 지수 구하기
        nas_prev_price, nas_current_price = await get_idx_data('^IXIC')
        nas_gap_price = round(nas_current_price - nas_prev_price, 2)
        nas_total_percent = round((nas_current_price - nas_prev_price) / nas_prev_price * 100, 2)
        
        total_msg = total_msg + "\n\n[NASDAQ]\n"
        total_msg = total_msg + " 전일 종가 : " + str(nas_prev_price) + "\n"
        total_msg = total_msg + " 금일 종가 : " + str(nas_current_price) + " / " + str(nas_gap_price) + " (" + str(nas_total_percent) + "%)"

        # 4. 러셀지수 구하기
        prev_price, current_price = await get_idx_data('^RUT')
        gap_price = round(current_price - prev_price, 2)
        total_percent = round((current_price - prev_price) / prev_price * 100, 2)
        
        total_msg = total_msg + "\n\n[Russell 2000]\n"
        total_msg = total_msg + " 전일 종가 : " + str(prev_price) + "\n"
        total_msg = total_msg + " 금일 종가 : " + str(current_price) + " / " + str(gap_price) + " (" + str(total_percent) + "%)"

        if user_id != 0:
            await dbgout_individual(total_msg, user_id)
        else:
            await send_msg(total_msg, "idx_flag")

    except Exception as ex:
        await dbgout("send_idx_info() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

async def alarm_info(user_id):
    """알림 설정 정보 전송"""
    try:

        conn = pymysql.connect(host=s_host, port=s_port, user=s_user, password=s_pass, db=s_db, charset=s_char)
        cur = conn.cursor()

        sql = "SELECT * FROM user_info WHERE user_id = " + str(user_id)

        cur.execute(sql)

        while(True):
            row = cur.fetchone()

            if row == None:
                break

            exc_str = ""
            idx_str = ""
            etf_str = ""

            if row[2] == 1:
                exc_str = "ON"
            else:
                exc_str = "OFF"

            if row[3] == 1:
                idx_str = "ON"
            else:
                idx_str = "OFF"

            if row[5] == 1:
                etf_str = "ON"
            else:
                etf_str = "OFF"

            total_msg = "[알림 설정 정보]\n"
            total_msg = total_msg + " 1. 환율 알림 : " + exc_str + "\n"
            total_msg = total_msg + " 2. 지수 알림 : " + idx_str + "\n"
            total_msg = total_msg + " 3. ETF 알림 : " + etf_str

            await dbgout_individual(total_msg, user_id)

    except Exception as ex:
        await dbgout("alarm_info() -> 함수 예외 발생! [내역 : " + str(ex) + "]")
    
    finally:
        conn.close()

async def chat_bot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """챗봇 로직"""
    try:
        user_text = update.message.text # 사용자가 보낸 메세지를 user_text 변수에 저장합니다.
        user_id = update.effective_chat.id

        if user_text == "환율" or user_text == "ㅎㅇ":
            await dbgout_individual("환율 데이터를 불러옵니다.", user_id)
            await dbgout_individual("로딩중...", user_id)
            await send_exchange_info(user_id)

        elif user_text == "지수" or user_text == "ㅈㅅ":
            await dbgout_individual("지수 데이터를 불러옵니다.", user_id)
            await dbgout_individual("로딩중...", user_id)
            await send_idx_info(user_id)

        elif user_text == "알림" or user_text == "ㅇㄹ":
            await alarm_info(user_id)

    except Exception as ex:
        await dbgout("chat_bot_handler() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """start 커맨드 로직"""
    try:
        start_chat_id = update.message.chat.id
        match_cnt = 0

        conn = pymysql.connect(host=s_host, port=s_port, user=s_user, password=s_pass, db=s_db, charset=s_char)
        cur = conn.cursor()

        sql = "SELECT * FROM user_info WHERE user_id = %s"

        cur.execute(sql, start_chat_id)

        while(True):
            row = cur.fetchone()

            if row == None:
               break

            if row[0] == start_chat_id:
                match_cnt += 1
                break
        
        if match_cnt == 0:
            insert_sql = """INSERT INTO user_info (user_id, tot_flag, exc_flag, idx_flag, etf_flag)
                                    VALUES (%s, %s, %s, %s, %s)"""
            insert_data = (start_chat_id, 0, 0, 0, 0)

            cur.execute(insert_sql, insert_data)
            conn.commit()

        await help_command(update, context)

    except Exception as ex:
        await dbgout("start_command() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

    finally:
        conn.close()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """help 커맨드 로직"""
    try:
        user_id = update.message.chat.id

        total_msg = "[명령어 안내]\n"
        total_msg = total_msg + "/exc : 환율알림 설정\n"
        total_msg = total_msg + "/idx : 지수알림 설정\n"
        total_msg = total_msg + "/etf : ETF알림 설정\n"
        total_msg = total_msg + "/gld : GLD ETF 정보조회\n"
        total_msg = total_msg + "/dbc : DBC ETF 정보조회\n"

        total_msg = total_msg + "\n[메세지 명령어 안내]\n"
        total_msg = total_msg + "1. '환율' or 'ㅎㅇ' : 환율정보 조회\n"
        total_msg = total_msg + "2. '지수' or 'ㅈㅅ' : 지수정보 조회\n"
        total_msg = total_msg + "3. '알림' or 'ㅇㄹ' : 알림 ON/OFF 정보 조회\n"

        await dbgout_individual(total_msg, user_id)

    except Exception as ex:
        await dbgout("help_command() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

async def exc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """환율 커맨드 로직"""
    try:
        show_list = []
        show_list.append(InlineKeyboardButton("1. on", callback_data="exc on")) # add on button
        show_list.append(InlineKeyboardButton("2. off", callback_data="exc off")) # add off button
        show_markup = InlineKeyboardMarkup(inline_keyboard=[show_list]) # make markup

        await update.message.reply_text("환율 알림 설정", reply_markup=show_markup)

    except Exception as ex:
        await dbgout("exc_command() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

async def idx_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """지수 커맨드 로직"""
    try:
        show_list = []
        show_list.append(InlineKeyboardButton("1. on", callback_data="idx on")) # add on button
        show_list.append(InlineKeyboardButton("2. off", callback_data="idx off")) # add off button
        show_markup = InlineKeyboardMarkup(inline_keyboard=[show_list]) # make markup

        await update.message.reply_text("지수 알림 설정", reply_markup=show_markup)

    except Exception as ex:
        await dbgout("idx_command() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

async def etf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """eft 커맨드 로직"""
    try:
        show_list = []
        show_list.append(InlineKeyboardButton("1. on", callback_data="etf on")) # add on button
        show_list.append(InlineKeyboardButton("2. off", callback_data="etf off")) # add off button
        show_markup = InlineKeyboardMarkup(inline_keyboard=[show_list]) # make markup

        await update.message.reply_text("ETF 알림 설정", reply_markup=show_markup)

    except Exception as ex:
        await dbgout("etf_command() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

async def gld_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """gld 커맨드 로직"""
    try:
        user_id = update.message.chat.id

        await dbgout_individual("로딩중...", user_id)

        gld_cur, gld_high, gld_avg, gld_low = await get_ft_data('GLD')

        total_msg = "[GLD ETF 정보]\n"
        total_msg = total_msg + " 52주 고점 : " + str(gld_high) + "\n"
        total_msg = total_msg + " 52주 평균 : " + str(gld_avg) + "\n"
        total_msg = total_msg + " 52주 저점 : " + str(gld_low) + "\n"
        total_msg = total_msg + " 현재가 : " + str(gld_cur)

        await dbgout_individual(total_msg, user_id)

    except Exception as ex:
        await dbgout("gld_command() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

async def dbc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """dbc 커맨드 로직"""
    try:
        user_id = update.message.chat.id

        await dbgout_individual("로딩중...", user_id)

        dbc_cur, dbc_high, dbc_avg, dbc_low = await get_ft_data('DBC')

        total_msg = "[DBC ETF 정보]\n"
        total_msg = total_msg + " 52주 고점 : " + str(dbc_high) + "\n"
        total_msg = total_msg + " 52주 평균 : " + str(dbc_avg) + "\n"
        total_msg = total_msg + " 52주 저점 : " + str(dbc_low) + "\n"
        total_msg = total_msg + " 현재가 : " + str(dbc_cur)
        
        await dbgout_individual(total_msg, user_id)

    except Exception as ex:
        await dbgout("dbc_command() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

async def alarm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """콜백 로직"""
    try:

        conn = pymysql.connect(host=s_host, port=s_port, user=s_user, password=s_pass, db=s_db, charset=s_char)
        cur = conn.cursor()

        user_id = update.effective_chat.id
        data_selected = update.callback_query.data

        await context.bot.send_chat_action(chat_id=update.effective_user.id, action=ChatAction.TYPING) # 입력중 표시

        if data_selected == "exc on":
            update_sql = "UPDATE user_info SET exc_flag = %s WHERE user_id = %s"
            update_data = (1, user_id)
            cur.execute(update_sql, update_data)
            conn.commit()

            await dbgout("환율정보 알림을 시작합니다.", user_id)

        elif data_selected == "exc off":
            update_sql = "UPDATE user_info SET exc_flag = %s WHERE user_id = %s"
            update_data = (0, user_id)
            cur.execute(update_sql, update_data)
            conn.commit()

            await dbgout("환율정보 알림을 종료합니다.", user_id)

        elif data_selected == "idx on":
            update_sql = "UPDATE user_info SET idx_flag = %s WHERE user_id = %s"
            update_data = (1, user_id)
            cur.execute(update_sql, update_data)
            conn.commit()

            await dbgout("지수정보 알림을 시작합니다.", user_id)

        elif data_selected == "idx off":
            update_sql = "UPDATE user_info SET idx_flag = %s WHERE user_id = %s"
            update_data = (0, user_id)
            cur.execute(update_sql, update_data)
            conn.commit()

            await dbgout("지수정보 알림을 종료합니다.", user_id)
            
        elif data_selected == "etf on":
            update_sql = "UPDATE user_info SET etf_flag = %s WHERE user_id = %s"
            update_data = (1, user_id)
            cur.execute(update_sql, update_data)
            conn.commit()

            await dbgout("ETF 시세알림을 시작합니다.", user_id)

        elif data_selected == "etf off":
            update_sql = "UPDATE user_info SET etf_flag = %s WHERE user_id = %s"
            update_data = (0, user_id)
            cur.execute(update_sql, update_data)
            conn.commit()

            await dbgout("ETF 시세알림을 종료합니다.", user_id)

    except Exception as ex:
        await dbgout("alarm_callback() -> 함수 예외 발생! [내역 : " + str(ex) + "]")

    finally:
        conn.close()

def search_etf(code):
    """현재가, 등락률 구하기"""

    try:
        # 네이버 ETF URL
        url = 'https://finance.naver.com/api/sise/etfItemList.nhn'

        json_data = json.loads(requests.get(url).text)
        df_etf_list = pd.json_normalize(json_data['result']['etfItemList'])

        df_etf_list = df_etf_list.set_index('itemcode')

        itemname = df_etf_list.loc[code].loc['itemname']
        nowVal = df_etf_list.loc[code].loc['nowVal']
        changeVal = df_etf_list.loc[code].loc['changeVal']
        changeRate = df_etf_list.loc[code].loc['changeRate']

        return itemname, nowVal, changeVal, changeRate

    except Exception as ex:
        asyncio.run(dbgout("search_etf() -> 함수 예외 발생! [내역 : " + str(ex) + "]"))

def get_low_val(code):
    """이동평균 구하기"""

    try:
        time_now = datetime.now()
        str_today = time_now.strftime('%Y.%m.%d')

        # 네이버 일별시세
        df = pd.DataFrame()
        sise_url = 'https://finance.naver.com/item/sise_day.nhn?code=' + code

        for page in range(1, 8):
            page_url = '{}&page={}'.format(sise_url, page)
            response_page = requests.get(page_url, headers={'User-agent': 'Mozilla/5.0'}).text
            df = pd.concat([df, pd.read_html(response_page)[0]])

        df = df.dropna() # n/a 제거
        df = df.reset_index(drop=True) # 인덱스 리셋
        df = df.rename(index=df['날짜'])

        if str_today == str(df.iloc[0].name):
            lastday = df.iloc[1].name
        else:
            lastday = df.iloc[0].name

        closes = df['종가'].sort_index()   
        ma_20 = closes.rolling(window=20).mean() # 20일 이동평균
        ma_60 = closes.rolling(window=60).mean() # 60일 이동평균

        ret_20 = round(ma_20.loc[lastday])
        ret_60 = round(ma_60.loc[lastday])

        code_name, cur_price, chan_val, chan_rate = search_etf(code)

        total_msg = ""
        if cur_price < ret_20 and cur_price < ret_60:
            total_msg = total_msg + "[" + code_name + "] \n※ 20일 이동평균 : " + str(ret_20) + "원"
            total_msg = total_msg + "\n※ 60일 이동평균 : " + str(ret_60) + "원"
            total_msg = total_msg + "\n※ 현재가 : " + str(cur_price) + "원"
            if chan_val > 0:
                chan_symbol = " ▲ "
            elif chan_val == 0:
                chan_symbol = " - "
            else:
                chan_symbol = " ▼ "

            total_msg = total_msg + chan_symbol + str(chan_val) + " (" + str(chan_rate) + "%)"

            asyncio.run(send_msg(total_msg, "etf_flag"))

    except Exception as ex:
        asyncio.run(dbgout("get_low_val() -> 함수 예외 발생! [내역 : " + str(ex) + "]"))

def send_low_var():
    try:
        # 360750 : TIGER 미국S&P500
        # 367380 : KINDEX 미국나스닥100
        # 305080 : TIGER 미국채10년선물
        # 132030 : KODEX 골드선물(H)
        symbol_list = ['360750', '367380', '305080', '132030']

        t_now = datetime.now()
        t_9 = t_now.replace(hour=8, minute=55, second=1, microsecond=0)
        t_exit = t_now.replace(hour=15, minute=34, second=0, microsecond=0)

        if (t_9 < t_now < t_exit):
            for sym in symbol_list:
                get_low_val(sym)
                time.sleep(1)

    except Exception as ex:
        asyncio.run(dbgout("send_low_var() -> 함수 예외 발생! [내역 : " + str(ex) + "]"))

def schedule_check():
    """ 스케쥴 루프 """
    try:
        # 스케쥴 로직
        while True:
            t_now = datetime.now()
            t_idx_start = t_now.replace(hour=7, minute=55, second=0, microsecond=0)
            t_idx_end = t_now.replace(hour=8, minute=5, second=0, microsecond=0)
            t_9 = t_now.replace(hour=8, minute=55, second=0, microsecond=0)
            t_exit = t_now.replace(hour=15, minute=35, second=0,microsecond=0)
            today = datetime.today().weekday()
            
            if today != 5 and today != 6:  # 토요일이나 일요일 제외

                # 지수 알림
                if t_idx_start < t_now < t_idx_end:
                    if (t_now.minute == 0 and 0 <= t_now.second <= 11):
                        asyncio.run(send_idx_info(0))
                        time.sleep(65)

                # 환율 알림
                if t_9 < t_now < t_exit: # 08:55 ~ 15:35 알림 작동 시간
                    if (t_now.minute == 30 and 0 <= t_now.second <= 11) or (t_now.minute == 0 and 0 <= t_now.second <= 11): # 30분마다 알림
                        asyncio.run(send_exchange_info(0))
                        time.sleep(65) # 65초

    except Exception as ex:
        asyncio.run(dbgout("schedule_check() -> 함수 예외 발생! [내역 : " + str(ex) + "]"))


if __name__ == '__main__': 
    try:
        # ETF 알림 관련 스레드 로직
        t1 = etf_alert_worker("ETF_ARERT_THREAD")
        t1.start()

        # 시간별 스케쥴 스레드 실행
        t2 = threading.Thread(target=schedule_check, args=())
        t2.start()

        # 텔레그램 챗봇 관련 로직
        application = ApplicationBuilder().token(s_token).build()

        start_handler = CommandHandler('start', start_command)
        application.add_handler(start_handler)

        help_handler = CommandHandler('help', help_command)
        application.add_handler(help_handler)

        exc_handler = CommandHandler('exc', exc_command)
        application.add_handler(exc_handler)

        idx_handler = CommandHandler('idx', idx_command)
        application.add_handler(idx_handler)

        etf_handler = CommandHandler('etf', etf_command)
        application.add_handler(etf_handler)

        gld_handler = CommandHandler('gld', gld_command)
        application.add_handler(gld_handler)

        dbc_handler = CommandHandler('dbc', dbc_command)
        application.add_handler(dbc_handler)

        application.add_handler(CallbackQueryHandler(alarm_callback))

        echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), chat_bot_handler)
        application.add_handler(echo_handler)

        application.run_polling()

    except Exception as ex:
        asyncio.run(dbgout("main -> exception!  [내역 : " + str(ex) + "]"))