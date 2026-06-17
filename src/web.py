import os
from flask import Flask, render_template_string
import db
import token_runner

app = Flask(__name__)

# Simple HTML templates
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
            <div class="stat"><b>Clients Active:</b> {{ active_clients }}</div>
            <div class="stat"><b>Stored Tokens:</b> {{ token_count }}</div>
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
        {% if tokens %}
        <table>
            <tr>
                <th>ID</th>
                <th>Token (Masked)</th>
                <th>Label</th>
                <th>Added</th>
            </tr>
            {% for token in tokens %}
            <tr>
                <td>{{ token.id }}</td>
                <td class="token">{{ token.masked }}</td>
                <td>{{ token.label or 'N/A' }}</td>
                <td>{{ token.added_at[:10] }}</td>
            </tr>
            {% endfor %}
        </table>
        <p><b>Total:</b> {{ tokens|length }} tokens stored</p>
        {% else %}
        <p>No tokens stored yet.</p>
        {% endif %}
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


@app.route('/')
def home():
    rows = db.list_tokens_sync()
    token_count = len(rows)
    active_clients = len(token_runner.clients)
    return render_template_string(HOME_HTML, token_count=token_count, active_clients=active_clients)


@app.route('/storage')
def storage():
    rows = db.list_tokens_sync()
    tokens = []
    for row in rows:
        token = row['token']
        masked = token[:4] + '...' + token[-4:] if len(token) > 8 else '****'
        tokens.append({
            'id': row['id'],
            'token': token,
            'masked': masked,
            'label': row['label'],
            'added_at': row['added_at']
        })
    return render_template_string(STORAGE_HTML, tokens=tokens)


@app.route('/help')
def help_page():
    return render_template_string(HELP_HTML)


def run_web_server(port=5000):
    """Run Flask server on the given port."""
    app.run(host='0.0.0.0', port=port, debug=False)
