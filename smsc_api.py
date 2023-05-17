import ssl
import warnings
import certifi
import asks
import click
import trio
from trio import TrioDeprecationWarning
import dotenv

SMS_URL = 'https://smsc.ru/sys/send.php'


@click.command
@click.option('--user', required=True, type=str)
@click.option('--api_password', required=True, type=str)
@click.option('--phones', required=True, type=str)
@click.option('--msg', required=True, type=str)
@click.option('--sms_ttl', default=1, type=int)
@click.option('--cost', default=0, type=int)
@click.option('--fmt', default=0, type=int)
def main(user, api_password, phones, msg, sms_ttl, cost, fmt):
    trio.run(send_sms, user, api_password, phones, msg, sms_ttl, cost, fmt)


async def send_sms(user, password, phones, msg, sms_ttl, cost, fmt):
    payload = {
        'login': user,
        'psw': password,
        'mes': msg,
        'valid': sms_ttl,
        'phones': phones,
        'cost': cost,
        'fmt': fmt,
    }
    resp = await asks.get(
        SMS_URL,
        params=payload,
        timeout=5,
        ssl_context=ssl_context,
        )
    resp.raise_for_status()
    print(resp.text)


# pylint: disable=E1120
if __name__ == '__main__':
    dotenv.load_dotenv()
    warnings.filterwarnings(action='ignore', category=TrioDeprecationWarning)
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    main(auto_envvar_prefix='SMSC')
