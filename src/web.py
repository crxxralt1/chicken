import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from src.bot import bot, data
import db
import token_runner

app = FastAPI(title='Discord Token Controller')

HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Token Controller Bot</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #0f0f0f; color: #fff; }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { color: #7289da; }
        .info { background: #2c2f33; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .stat { margin: 10px 0; font-size: 16px; }
        a { color: #7289da; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Discord Token Controller Bot</h1>
        <div class="info">
            <div class="stat"><b>Status:</b> ✅ Running</div>
            <div class="stat"><b>Clients Active:</b> {active_clients}</div>
            <div class="stat"><b>Stored Tokens:</b> {token_count}</div>
        </div>
        <div class="info">
            <h3>Navigation</h3>
            <ul>
                <li><a href="/storage">View Token Storage</a></li>
                <li><a href="/help">Bot Commands</a></li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

STORAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Token Storage</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #0f0f0f; color: #fff; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #7289da; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #2c2f33; }
        tr:hover { background: #23272a; }
        .token { font-family: monospace; }
        a { color: #7289da; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Token Storage</h1>
        <p><a href="/">← Back</a></p>
        {token_rows}
    </div>
</body>
</html>
"""

HELP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Bot Commands</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #0f0f0f; color: #fff; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #7289da; }
        .category { background: #2c2f33; padding: 15px; margin: 15px 0; border-radius: 5px; }
        .cmd { margin: 10px 0; font-family: monospace; color: #99aab5; }
        .desc { color: #aaa; margin-left: 20px; }
        a { color: #7289da; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Bot Commands</h1>
        <p><a href="/">← Back</a></p>
        
        <div class="category">
            <h3>Token Management</h3>
            <div class="cmd">!addtoken &lt;token&gt; [label]</div>
            <div class="desc">Add a token with optional label</div>
            <div class="cmd">!rmtoken &lt;id|token&gt;</div>
            <div class="desc">Remove token by ID or exact token</div>
            <div class="cmd">!listtokens</div>
            <div class="desc">List all stored tokens (masked)</div>
        </div>

        <div class="category">
            <h3>Bulk Commands</h3>
            <div class="cmd">!runtokens</div>
            <div class="desc">Start all stored token clients</div>
            <div class="cmd">!joinvc &lt;channel_name&gt;</div>
            <div class="desc">All tokens join a voice channel</div>
        </div>

        <div class="category">
            <h3>Per-Token Commands</h3>
            <div class="cmd">!runtoken &lt;tokenid&gt;</div>
            <div class="desc">Start a specific token</div>
            <div class="cmd">!joinvc_token &lt;tokenid&gt;</div>
            <div class="desc">Token joins your current VC</div>
            <div class="cmd">!joinsv &lt;tokenid&gt; &lt;invite_url&gt;</div>
            <div class="desc">Token joins a server</div>
            <div class="cmd">!say &lt;tokenid&gt; &lt;userid&gt; &lt;message&gt;</div>
            <div class="desc">Token sends DM to user</div>
        </div>
    </div>
</body>
</html>
"""


@app.get('/', response_class=HTMLResponse)
def home():
    rows = db.list_tokens_sync()
    active_clients = len(token_runner.clients)
    return HTMLResponse(content=HOME_HTML.format(active_clients=active_clients, token_count=len(rows)))


@app.get('/storage', response_class=HTMLResponse)
def storage():
    rows = db.list_tokens_sync()
    if not rows:
        token_rows = '<p>No tokens stored yet.</p>'
    else:
        row_html = '<table>\n            <tr>\n                <th>ID</th>\n                <th>Token (Masked)</th>\n                <th>Label</th>\n                <th>Added</th>\n            </tr>\n'
        for row in rows:
            token = row['token']
            masked = token[:4] + '...' + token[-4:] if len(token) > 8 else '****'
            label = row['label'] or 'N/A'
            added_at = row['added_at'][:10] if row['added_at'] else ''
            row_html += f'            <tr>\n                <td>{row["id"]}</td>\n                <td class="token">{masked}</td>\n                <td>{label}</td>\n                <td>{added_at}</td>\n            </tr>\n'
        row_html += f'        </table>\n        <p><b>Total:</b> {len(rows)} tokens stored</p>\n'
        token_rows = row_html

    content = STORAGE_HTML.format(token_rows=token_rows)
    return HTMLResponse(content=content)


@app.get('/help', response_class=HTMLResponse)
def help_page():
    return HTMLResponse(content=HELP_HTML)


async def _start_controller_bot():
    controller_token = os.environ.get('CONTROLLER_TOKEN') or data.get('controller_token')
    if not controller_token:
        raise RuntimeError('CONTROLLER_TOKEN must be set as an environment variable for deployment.')
    print('[web] Starting controller bot')
    try:
        await bot.start(controller_token)
    except Exception as exc:
        print(f'[web] Controller bot failed to start: {exc}')
        raise


@app.on_event('startup')
async def startup_event():
    if getattr(app.state, 'bot_task', None) is None:
        app.state.bot_task = asyncio.create_task(_start_controller_bot())


@app.on_event('shutdown')
async def shutdown_event():
    if getattr(app.state, 'bot_task', None) is not None:
        await bot.close()
        app.state.bot_task.cancel()
