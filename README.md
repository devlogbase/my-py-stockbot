# 🤖 MyPyStockbot

![프로그램 실행 예시](https://github.com/devlogbase/my-py-stockbot/assets/155949809/50f97302-8a72-4701-8e3a-9d3297d43a2d)
![프로그램 실행 예시2](https://github.com/devlogbase/my-py-stockbot/assets/155949809/3cf5c659-132a-491f-9f8c-6decd6701239)

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
- <a href="https://github.com/ranaroussi/">yfinance</a> : 야후 파이낸스 라이브러리

<br/>

## 기능 설명

- `/start` : 채팅방 입장시 Start 명령어가 입력되며 입장한 User의 Chat ID가 데이터베이스로 Insert 됩니다. (추후 알림 On/Off에 사용)
- `/help` : 채팅방 명령어를 안내해 주는 메시지가 뜹니다.
- `/exc` 또는 `ㅎㅇ`, `환율` 입력 : 원/달러 환율 정보를 보여줍니다.
- `/idx` : 주가지수를 불러와 보여줍니다. (다우, 나스닥, 러셀2000 지수)
- `/etf` : 설정한 ETF의 저가 알림 기능을 On/Off 설정하는 메뉴를 보여줍니다.
- `/gld` : GLD ETF의 가격 정보를 보여줍니다.
- `/dbc` : DBC ETF의 가격 정보를 보여줍니다.
- 