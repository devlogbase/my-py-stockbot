# 🤖 MyPyStockbot

<br/>

<figure class="half">
<a href="link"><img src="https://github.com/devlogbase/my-py-stockbot/assets/155949809/298f26e2-fe94-41fb-979e-324372b3f4a6"></a>
<a href="link"><img src="https://github.com/devlogbase/my-py-stockbot/assets/155949809/320ae39d-e639-4e03-9a9f-84c720399bb7"></a>
</figure>

<br/>
<br/>

## 📢 프로그램 소개

- 주식 관련 정보를 알려주는 텔레그램 챗봇 프로그램입니다.
- 주가지수, 환율정보 및 ETF 가격 체크 등의 기능을 지원합니다.
- 데이터 베이스를 이용하여 사용자별 알람 On/Off 기능을 제공합니다.

<br/>

## 💻️ 기술 스택

<p>
<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=Python&logoColor=white">
<img src="https://img.shields.io/badge/mysql-4479A1?style=for-the-badge&logo=mysql&logoColor=white">
<img src="https://img.shields.io/badge/linux-FCC624?style=for-the-badge&logo=linux&logoColor=black">
</p>

<br/>

## 📚 파이썬 버전 및 필요 라이브러리

- Python : 3.6 버전 이상
- <a href="https://python-telegram-bot.org/">python-telegram-bot</a> : 텔레그램 관련 라이브러리
- <a href="https://github.com/ranaroussi/yfinance/">yfinance</a> : 야후 파이낸스 라이브러리

<br/>

## ⚙️ 기능 설명

- `/start` : 채팅방 입장시 Start 명령어가 입력되며 입장한 User의 Chat ID가 데이터베이스로 Insert 됩니다. (추후 알림 On/Off에 사용)
- `/help` : 채팅방 명령어를 안내해 주는 메시지가 뜹니다.
- `/exc` 또는 `환율`, `ㅎㅇ` 입력 : 원/달러 환율 정보를 보여줍니다.
- `/idx` 또는 `지수`, `ㅈㅅ` 입력 : 주가지수를 불러와 보여줍니다. (다우, S&P500, 나스닥 지수)
- `/etf` : 설정한 ETF의 저가 알림 기능을 On/Off 설정하는 메뉴를 보여줍니다.
- `/gld` : GLD ETF의 가격 정보를 보여줍니다.
- `/dbc` : DBC ETF의 가격 정보를 보여줍니다.

<br/>

