from quart import Quart

try:
    import ujson as json
except ImportError:
    import json


with open('config.json') as f:
    conf = json.load(f)

app = Quart(__name__)

import bot.hooks
