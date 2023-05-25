from quart import websocket
from quart_trio import QuartTrio

app = QuartTrio(__name__)

@app.route('/')
async def hello():
    return 'hello'

@app.websocket('/ws')
async def ws():
    while True:
        await websocket.send('hello')

app.run()
