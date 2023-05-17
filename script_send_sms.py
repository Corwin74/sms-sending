import ssl
import warnings
import certifi
import asks
import click
import trio
from trio import TrioDeprecationWarning
import dotenv


payload = {
    'cost': 0,
    'fmt': 3,
}


@click.command
@click.option('--user')
@click.option('--api_password')
@click.option('--sms_ttl')
@click.argument('phones')
@click.argument('msg')
def main(user, api_password, phones, msg, sms_ttl):
    trio.run(send_sms, user, api_password, phones, msg, sms_ttl)


async def send_sms(user, password, phones, msg, sms_ttl):
    payload['login'] = user
    payload['psw'] = password
    payload['mes'] = msg
    payload['valid'] = sms_ttl
    payload['phones'] = phones
    resp = await asks.get(
        SMS_URL,
        params=payload,
        timeout=5,
        ssl_context=ssl_context,
        )
    resp.raise_for_status()
    print(resp.text)


if __name__ == '__main__':
    dotenv.load_dotenv()
    warnings.filterwarnings(action='ignore', category=TrioDeprecationWarning)
    SMS_URL = 'https://smsc.ru/sys/send.php'
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    main(auto_envvar_prefix='SMSC')
