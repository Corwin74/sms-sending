import ssl
import warnings
import certifi
import asks
import click
import trio
from trio import TrioDeprecationWarning
import dotenv

SMS_URL = 'https://smsc.ru/sys/send.php'
STATUS_URL = 'https://smsc.ru/sys/status.php'


class UnexpectedAPIResponse(AttributeError):
    pass


@click.command
@click.option('--user', required=True, type=str)
@click.option('--api_password', required=True, type=str)
@click.option('--sender', default='SMSC.RU')
@click.option('--phones', required=True, type=str)
@click.option('--msg', required=True, type=str)
@click.option('--sms_ttl', default=1, type=int)
def main(user, api_password, phones, sender, msg, sms_ttl):
    trio.run(
        send_sms,
        user,
        api_password,
        phones,
        sender,
        msg,
        sms_ttl,
    )


async def send_sms(user, password, phones, sender, msg, sms_ttl):
    payload = {
        'login': user,
        'psw': password,
        'sender': sender,
        'mes': msg,
        'valid': sms_ttl,
        'phones': phones,
        'fmt': 3,
    }
    resp = await asks.get(
        SMS_URL,
        params=payload,
        timeout=5,
        ssl_context=ssl_context,
        )
    resp.raise_for_status()
    parced_resp = resp.json()
    print(parced_resp)
    if 'error' in parced_resp:
        print(parced_resp)
        return None
    if 'id' in parced_resp and 'cnt' in parced_resp:
        status = await get_sms_status(
            user,
            password,
            phones,
            parced_resp['id'],
        )
        print(status)
        return status['status']
    raise UnexpectedAPIResponse


async def get_sms_status(user, password, phones, sms_id):
    payload = {
        'login': user,
        'psw': password,
        'id': sms_id,
        'phone': phones,
        'fmt': 3,
    }
    resp = await asks.get(
        STATUS_URL,
        params=payload,
        timeout=5,
        ssl_context=ssl_context,
    )
    resp.raise_for_status()
    return resp.json()


# pylint: disable=E1120
if __name__ == '__main__':
    dotenv.load_dotenv()
    warnings.filterwarnings(action='ignore', category=TrioDeprecationWarning)
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    main(auto_envvar_prefix='SMSC')
