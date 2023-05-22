import os
import warnings
import json
from contextvars import ContextVar
from unittest.mock import patch
from quart import request, websocket
from quart_trio import QuartTrio
import trio
from trio import TrioDeprecationWarning
import dotenv
from smsc_api import request_smsc, request_smsc_side_effect
from dataclasses import dataclass
from quart_schema import QuartSchema, validate_request, DataSource


@dataclass
class SmsText:
    text: int


app = QuartTrio(__name__)
QuartSchema(app, convert_casing=True)
smsc_login = ContextVar('smsc_login')
smsc_password = ContextVar('smsc_password')
ssl_context = ContextVar('ssl_context')


@app.route('/')
async def hello():
    async with await trio.open_file('index.html') as f:
        page = await f.read()
    return page


@app.websocket('/ws')
async def ws():
    while True:
        await trio.sleep(5)
        await websocket.send('''
    {
        "msgType": "SMSMailingStatus", "SMSMailings": [
        {
        "timestamp": 1123131392.734,
        "SMSText": "Сегодня гроза! Будьте осторожны!",
        "mailingId": "1",
        "totalSMSAmount": 345,
        "deliveredSMSAmount": 47,
        "failedSMSAmount": 5
        },
        {
        "timestamp": 1323141112.924422,
        "SMSText": "Новогодняя акция!!! Приходи в магазин и получи скидку!!!",
        "mailingId": "new-year",
        "totalSMSAmount": 3993,
        "deliveredSMSAmount": 801,
        "failedSMSAmount": 0
        }
    ] 
    }''')


@app.route('/send/', methods=['POST'])
@validate_request(SmsText, source=DataSource.FORM)
async def send(data: SmsText):
    print(data)
    form = await request.form
    with patch('__main__.request_smsc') as mock_func:
        mock_func.side_effect = request_smsc_side_effect
        payload = {'msg': form['text']}
        parced_resp = await request_smsc(
            'GET',
            'send',
            payload=payload,
        )
    print(f'Отправлено SMS c текстом: {form["text"]}')
    return parced_resp


if __name__ == '__main__':
    dotenv.load_dotenv()
    smsc_login.set(os.environ['SMSC_USER'])
    smsc_password.set(os.environ['SMSC_API_PASSWORD'])
    warnings.filterwarnings(action='ignore', category=TrioDeprecationWarning)
    app.run()
