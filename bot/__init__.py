from aiomirai import HttpSessionApi
from quart import Quart

try:
    import ujson as json
except ImportError:
    import json


with open('config.json') as f:
    conf = json.load(f)

app = Quart(__name__)
api = HttpSessionApi(**conf['mirai'])

@app.before_serving
async def _():
    await api.auth()
    await api.verify()

import bot.view
