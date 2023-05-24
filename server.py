import os
import warnings
from contextvars import ContextVar
from unittest.mock import patch
from quart import websocket
from quart_trio import QuartTrio
import trio
from trio import TrioDeprecationWarning
import dotenv
from pydantic import BaseModel, validator
from quart_schema import (
    QuartSchema,
    validate_request,
    DataSource,
    RequestSchemaValidationError,
)
from smsc_api import request_smsc, request_smsc_side_effect


class PySmsText(BaseModel):
    text: str

    @validator('text')
    @classmethod
    def check_text_lenght(cls, sms_text_input):
        if not 0 < len(sms_text_input) < 160:
            raise ValueError('SMS text must be 1-160 symbols')
        return sms_text_input


app = QuartTrio(__name__)
QuartSchema(app)
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
    first_c = 0
    second_c = 0
    while True:
        await trio.sleep(1)
        if first_c < 346:
            first_c += 3
        else:
            first_c = 0
        if second_c < 3994:
            second_c += 40
        else:
            second_c = 0
        stub = '''
        {
            "msgType": "SMSMailingStatus", "SMSMailings": [
            {
            "timestamp": 1123131392.734,
            "SMSText": "Сегодня гроза! Будьте осторожны!",
            "mailingId": "1",
            "totalSMSAmount": 345,
            "deliveredSMSAmount":'''+str(first_c)+''',
            "failedSMSAmount": 5
            },
            {
            "timestamp": 1323141112.924422,
            "SMSText": "Новогодняя акция! Приходи в магазин и получи скидку!",
            "mailingId": "new-year",
            "totalSMSAmount": 3993,
            "deliveredSMSAmount": '''+str(second_c)+''',
            "failedSMSAmount": 0
            }
        ]
        }'''
        await websocket.send(stub)


@app.route('/send/', methods=['POST'])
@validate_request(PySmsText, source=DataSource.FORM)
async def send(data: PySmsText):
    with patch('__main__.request_smsc') as mock_func:
        mock_func.side_effect = request_smsc_side_effect
        payload = {'msg': data.text}
        parced_resp = await request_smsc(
            'GET',
            'send',
            payload=payload,
        )
    print(f'Отправлено SMS c текстом: {data.text}')
    return parced_resp


@app.errorhandler(RequestSchemaValidationError)
async def handle_request_validation_error(_):
    return {"errorMessage": "Validation error!"}, 400


if __name__ == '__main__':
    dotenv.load_dotenv()
    smsc_login.set(os.environ['SMSC_USER'])
    smsc_password.set(os.environ['SMSC_API_PASSWORD'])
    warnings.filterwarnings(action='ignore', category=TrioDeprecationWarning)
    app.run()
