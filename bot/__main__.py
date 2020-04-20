from bot import app, conf

app.run(**(conf.get('app') or {}))
