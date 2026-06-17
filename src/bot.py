
import os
import json
import asyncio
import threading
from discord.ext import commands
from discord.ext.commands import CommandInvokeError
import token_runner
import discord
import db
import web

CONFIG_PATH = os.path.join(os.getcwd(), 'data', 'config.json')


def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=2)


data = load_config()

# ensure DB exists
db.ensure_db()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'[controller] Logged in as {bot.user} (id: {bot.user.id})')
    # start web server in background thread if not already running
    if not hasattr(on_ready, 'web_started'):
        port = int(os.environ.get('PORT', 5000))
        web_thread = threading.Thread(target=web.run_web_server, args=(port,), daemon=True)
        web_thread.start()
        on_ready.web_started = True
        print(f'[web] Server started on http://0.0.0.0:{port}')


@bot.command(name='h')
async def help_cmd(ctx):
    """Show all available commands and setup instructions."""
    help_text = """
**Discord Token Controller Bot — Commands & Setup**

**Setup:**
1. Add tokens: `!addtoken <token> [label]`
2. Start all tokens: `!runtokens`
3. Check stored tokens: `!listtokens`

**Token Management (owner only):**
- `!addtoken <token> [label]` — add a token with optional label
- `!rmtoken <id|token>` — remove token by ID or exact token
- `!listtokens` — list all stored tokens (masked)
- `!exportconfig` — export tokens to data/config.json
- `!importconfig` — import tokens from data/config.json

**Bulk Commands (owner only):**
- `!runtokens` — start all stored token clients
- `!joinvc <channel_name>` — all tokens join a voice channel (plays TTS 5x with 30s cooldown, then leaves)

**Per-Token Commands (owner only):**
- `!runtoken <tokenid>` — start a specific token
- `!joinvc_token <tokenid>` — token joins your current VC (plays TTS 5x with 30s cooldown, then leaves)
- `!joinsv <tokenid> <invite_url>` — token joins a server
- `!say <tokenid> <userid> <message>` — token sends DM to user

**Deploy on Railway:**
- Set env var: `CONTROLLER_TOKEN = your-controller-bot-token`
- Ensure ffmpeg is available in the runtime
- Tokens are persisted in `data/tokens.db`
"""
    await ctx.send(help_text)


@bot.command(name='listc')
async def list_commands(ctx):
    """List all commands with descriptions in an embed."""
    embed = discord.Embed(
        title='Command List',
        description='All available commands for the Token Controller Bot',
        color=discord.Color.blue()
    )
    
    commands_data = {
        'General': [
            ('!h', 'Show help and setup instructions'),
            ('!listc', 'List all commands in this embed'),
        ],
        'Token Management': [
            ('!addtoken <token> [label]', 'Add a token with optional label'),
            ('!rmtoken <id|token>', 'Remove token by ID or exact token'),
            ('!listtokens', 'List all stored tokens (masked)'),
            ('!exportconfig', 'Export tokens to data/config.json'),
            ('!importconfig', 'Import tokens from data/config.json'),
        ],
        'Bulk Commands (owner)': [
            ('!runtokens', 'Start all stored token clients'),
            ('!joinvc <channel_name>', 'All tokens join a VC (plays TTS 5x w/ 30s cooldown)'),
        ],
        'Per-Token Commands (owner)': [
            ('!runtoken <tokenid>', 'Start a specific token'),
            ('!joinvc_token <tokenid>', 'Token joins your current VC (plays TTS 5x w/ 30s cooldown)'),
            ('!joinsv <tokenid> <invite_url>', 'Token joins a server'),
            ('!say <tokenid> <userid> <message>', 'Token sends DM to user'),
        ],
    }
    
    for category, cmds in commands_data.items():
        field_value = '\n'.join(f'`{cmd}` — {desc}' for cmd, desc in cmds)
        embed.add_field(name=category, value=field_value, inline=False)
    
    embed.set_footer(text='Owner-only commands require bot owner permissions')
    await ctx.send(embed=embed)



@bot.command(name='addtoken')
async def addtoken(ctx, token: str, *, label: str = None):
    # add token to persistent DB with optional label
    added = await asyncio.to_thread(db.add_token_sync, token, label)
    if added:
        await ctx.send('Token added to persistent storage.')
    else:
        await ctx.send('Token already exists in storage.')


@bot.command(name='rmtoken')
async def rmtoken(ctx, identifier: str):
    """Remove a stored token by id or by exact token string."""
    # try id first
    removed = False
    if identifier.isdigit():
        removed = await asyncio.to_thread(db.remove_token_by_id_sync, int(identifier))
    if not removed:
        removed = await asyncio.to_thread(db.remove_token_sync, identifier)
    if removed:
        await ctx.send('Token removed.')
    else:
        await ctx.send('No matching token found.')

@bot.command(name='runtokens')
async def runtokens(ctx):
    rows = await asyncio.to_thread(db.list_tokens_sync)
    if not rows:
        await ctx.send('No tokens found in persistent storage.')
        return
    tokens = [r['token'] for r in rows]
    token_ids = [r['id'] for r in rows]
    await ctx.send(f'Starting {len(tokens)} clients...')
    loop = asyncio.get_event_loop()
    loop.create_task(token_runner.start_clients(tokens, token_ids=token_ids))
    await ctx.send('Token clients launched (in background).')


@bot.command(name='listtokens')
async def listtokens(ctx):
    rows = await asyncio.to_thread(db.list_tokens_sync)
    if not rows:
        await ctx.send('No tokens stored.')
        return
    def mask(t: str) -> str:
        if len(t) <= 8:
            return '****'
        return t[:4] + '...' + t[-4:]

    lines = []
    for r in rows[:50]:
        label = f"({r.get('label')})" if r.get('label') else ''
        lines.append(f"{r.get('id')}: {mask(r.get('token'))} {label}")
    if len(rows) > 50:
        lines.append(f"...and {len(rows)-50} more")
    await ctx.send(f'Stored tokens: {len(rows)}\n' + '\n'.join(lines))



@bot.command(name='exportconfig')
async def exportconfig(ctx):
    await asyncio.to_thread(db.export_to_config_sync)
    await ctx.send('Exported tokens to data/config.json')


@bot.command(name='importconfig')
async def importconfig(ctx):
    added = await asyncio.to_thread(db.import_from_config_sync)
    await ctx.send(f'Imported {added} tokens from data/config.json')


@bot.command(name='exportconfig')
async def exportconfig(ctx):
    rows = await asyncio.to_thread(db.list_tokens_sync)
    config = load_config()
    config['tokens'] = [
        {'token': row['token'], 'label': row['label']} if row['label'] else row['token']
        for row in rows
    ]
    save_config(config)
    await ctx.send(f'Exported {len(rows)} tokens to data/config.json.')


@bot.command(name='importconfig')
async def importconfig(ctx):
    config = load_config()
    raw_tokens = config.get('tokens', [])
    added = 0
    for item in raw_tokens:
        if isinstance(item, str):
            token, label = item, None
        elif isinstance(item, dict):
            token = item.get('token')
            label = item.get('label')
        else:
            continue
        if not token:
            continue
        inserted = await asyncio.to_thread(db.add_token_sync, token, label)
        if inserted:
            added += 1
    await ctx.send(f'Imported {added} new tokens from config.')


@bot.command(name='joinvc')
async def joinvc(ctx, *, channel_name: str):
    # find voice channel by name in the guild where command was invoked
    guild = ctx.guild
    if guild is None:
        await ctx.send('This command must be used in a guild.')
        return
    match = discord.utils.get(guild.voice_channels, name=channel_name)
    if match is None:
        await ctx.send(f'Voice channel "{channel_name}" not found in this guild.')
        return
    # instruct token clients to join the channel id and await results
    await ctx.send(f'Instructing clients to join voice channel {match.name}...')
    results = await token_runner.join_channel(match.id)
    success = sum(1 for r in results if r.get('success'))
    fail = len(results) - success
    summary_lines = [f"Success: {success}, Failures: {fail}"]
    # include up to first 10 detailed messages
    for r in results[:10]:
        summary_lines.append(f"{r.get('user')}: {r.get('msg')}")
    if len(results) > 10:
        summary_lines.append(f"...and {len(results)-10} more results")
    await ctx.send('\n'.join(summary_lines))


@bot.command(name='runtoken')
async def runtoken(ctx, token_id: int):
    """Start a specific token by ID."""
    rows = await asyncio.to_thread(db.list_tokens_sync)
    token_row = None
    for r in rows:
        if r['id'] == token_id:
            token_row = r
            break
    if not token_row:
        await ctx.send(f'Token ID {token_id} not found.')
        return
    result = await token_runner.run_token_by_id(token_id, token_row['token'])
    await ctx.send(result['msg'])


@bot.command(name='joinvc_token')
async def joinvc_token(ctx, token_id: int):
    """Make a specific token client join the user's current voice channel."""
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send('You must be in a voice channel.')
        return
    channel_id = ctx.author.voice.channel.id
    result = await token_runner.join_channel_by_token_id(token_id, channel_id)
    await ctx.send(result['msg'])


@bot.command(name='joinsv')
async def joinsv(ctx, token_id: int, *, invite_url: str):
    """Make a specific token join a server via invite link."""
    result = await token_runner.join_server_by_token_id(token_id, invite_url)
    await ctx.send(result['msg'])


@bot.command(name='say')
async def say(ctx, token_id: int, user_id: int, *, message: str):
    """Send a DM message via a specific token to a user."""
    result = await token_runner.send_message_by_token_id(token_id, user_id, message)
    await ctx.send(result['msg'])


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandInvokeError):
        await ctx.send(f'Command error: {error.original}')
    else:
        await ctx.send(f'Error: {error}')


if __name__ == '__main__':
    # prefer environment variable for deploy platforms like Railway
    controller_token = os.environ.get('CONTROLLER_TOKEN') or data.get('controller_token')
    if not controller_token:
        print('Please set CONTROLLER_TOKEN environment variable or controller_token in data/config.json')
        raise SystemExit(1)
    bot.run(controller_token)
