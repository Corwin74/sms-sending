from quart import render_template, websocket
from quart_trio import QuartTrio
import trio

app = QuartTrio(__name__)


@app.route("/")
async def hello():
    async with await trio.open_file('index.html') as f:
        page = await f.read()
    return page


@app.websocket("/ws")
async def ws():
    while True:
        await websocket.send("hello")
        await websocket.send_json({"hello": "world"})


if __name__ == "__main__":
    app.run()
