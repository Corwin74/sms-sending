import ssl
import warnings
from contextvars import ContextVar
from unittest.mock import patch
import certifi
import asks
import asyncclick as click
import trio
from trio import TrioDeprecationWarning
import dotenv

SEND_URL = 'https://smsc.ru/sys/send.php'
STATUS_URL = 'https://smsc.ru/sys/status.php'
JSON_ANSWER_FORMAT = 3

smsc_login = ContextVar('smsc_login')
smsc_password = ContextVar('smsc_password')
ssl_context = ContextVar('ssl_context')


class SmscApiError(Exception):
    pass


async def request_smsc(
    http_method,
    api_method,
    *,
    login=None,
    password=None,
    payload=None,
):

    if api_method == 'send':
        url = SEND_URL
    elif api_method == 'status':
        url = STATUS_URL
    else:
        raise SmscApiError

    if payload is None:
        payload = {}
    if 'fmt' not in payload:
        payload['fmt'] = JSON_ANSWER_FORMAT
    payload['login'] = login or smsc_login.get()
    payload['psw'] = password or smsc_password.get()

    resp = await asks.request(
        http_method,
        url,
        params=payload,
        timeout=5,
        ssl_context=ssl_context.get(),
    )
    resp.raise_for_status()
    return resp.json()


# pylint: disable=w0613
def request_smsc_side_effect(*args, **kwargs):
    if args[1] == 'send':
        return {'id': 52, 'cnt': 1}
    if args[1] == 'status':
        return {
            'status': -1,
            'last_date': '21.05.2023 19:16:17',
            'last_timestamp': 1684685777,
            'flag': 0,
            'err': 200
        }
    raise SmscApiError
# pylint: enable=w0613


@click.command
@click.option('--user', required=True, type=str, envvar='SMSC_USER')
@click.option(
    '--api_password',
    required=True,
    type=str,
    envvar='SMSC_API_PASSWORD',
)
@click.option('--sender', default='SMSC.RU')
@click.option('--phones', required=True, type=str)
@click.option('--msg', required=True, type=str)
@click.option('--sms_ttl', default=1, type=int)
async def main(user, api_password, phones, sender, msg, sms_ttl):
    smsc_login.set(user)
    smsc_password.set(api_password)
    ssl_context.set(ssl.create_default_context(cafile=certifi.where()))
    payload = {
        'sender': sender,
        'mes': msg,
        'valid': sms_ttl,
        'phones': phones,
    }

    with patch('__main__.request_smsc') as mock_func:
        mock_func.side_effect = request_smsc_side_effect
        parced_resp = await request_smsc(
            'GET',
            'send',
            payload=payload,
        )
        print(parced_resp)

    if 'error' in parced_resp:
        raise SmscApiError
    if 'id' in parced_resp and 'cnt' in parced_resp:
        with patch('__main__.request_smsc') as mock_func:
            mock_func.side_effect = request_smsc_side_effect
            status = await request_smsc(
                'GET',
                'status',
                payload={
                    'phone': phones,
                    'id': parced_resp['id'],
                },
            )
            print(status)
            return status['status']
    raise SmscApiError


# pylint: disable=E1120
if __name__ == '__main__':
    dotenv.load_dotenv()
    warnings.filterwarnings(action='ignore', category=TrioDeprecationWarning)
    main(_anyio_backend="trio")
