import os
import warnings
import json
from trio import TrioDeprecationWarning
from contextvars import ContextVar
from unittest.mock import patch
import asyncio
import aioredis
import trio
import trio_asyncio
from hypercorn.trio import serve
from hypercorn.config import Config as HyperConfig
import dotenv
from pydantic import BaseModel, validator
from quart_schema import (
    QuartSchema,
    validate_request,
    DataSource,
    RequestSchemaValidationError,
)
from smsc_api import request_smsc, request_smsc_side_effect
from db import Database
# pylint: disable=C0413
warnings.filterwarnings(
    action='ignore',
    category=TrioDeprecationWarning
)
from quart import websocket
from quart_trio import QuartTrio


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
sms_db_context = ContextVar('sms_db')


def get_sms_delivery_report(mailing):
    pendning_count = 0
    delivered_count = 0
    failed_count = 0
    for _, status in mailing['phones'].items():
        if status == 'pending':
            pendning_count += 1
        elif status == 'delivered':
            delivered_count += 1
        elif status == 'failed':
            failed_count += 1
        else:
            raise ValueError(f'Wrong status: {status}')
    return (pendning_count, delivered_count, failed_count)


@app.route('/')
async def hello():
    async with await trio.open_file('index.html') as f:
        page = await f.read()
    return page


@app.websocket('/ws')
async def ws():
    while True:
        await trio.sleep(1)
        sms_db = sms_db_context.get()
        sms_ids = await trio_asyncio.aio_as_trio(
            sms_db.list_sms_mailings()
        )
        sms_mailings = await trio_asyncio.aio_as_trio(
            sms_db.get_sms_mailings(*sms_ids)
        )
        mailing_status = []
        for mailing in sms_mailings:
            sms_delivery_report = get_sms_delivery_report(mailing)
            mailing_status.append(
                {
                    "timestamp": mailing['created_at'],
                    "SMSText": mailing['text'],
                    "mailingId": str(mailing['sms_id']),
                    "totalSMSAmount": mailing['phones_count'],
                    "deliveredSMSAmount": sms_delivery_report[1],
                    "failedSMSAmount": sms_delivery_report[2]
                }
            )
        message = {
            "msgType": "SMSMailingStatus",
            "SMSMailings": mailing_status
        }
        await websocket.send(json.dumps(message))


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
    sms_db = sms_db_context.get()
    print(f'Отправлено SMS c текстом: {data.text}')
    sms_id = parced_resp['id']
    phones = [
            '+79057589746',
    ]
    text = data.text
    await trio_asyncio.aio_as_trio(
        sms_db.add_sms_mailing(sms_id, phones, text)
    )
    sms_ids = await trio_asyncio.aio_as_trio(
        sms_db.list_sms_mailings()
    )
    print('Registered mailings ids', sms_ids)
    return parced_resp


@app.errorhandler(RequestSchemaValidationError)
async def handle_request_validation_error(_):
    return {"errorMessage": "Validation error!"}, 400


async def run_server():
    async with trio_asyncio.open_loop() as loop:
        assert loop == asyncio.get_event_loop()
        dotenv.load_dotenv()
        smsc_login.set(os.environ['SMSC_USER'])
        smsc_password.set(os.environ['SMSC_API_PASSWORD'])
        redis = await trio_asyncio.aio_as_trio(
            aioredis.from_url(
                os.environ['REDIS_URL'],
                decode_responses=True
            )
        )
        sms_db_context.set(Database(redis))

        config = HyperConfig()
        config.bind = ['127.0.0.1:5000']
        config.use_reloader = True
        await serve(app, config)


if __name__ == '__main__':
    trio.run(run_server)
