from keep_alive import keep_alive
keep_alive()

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import io
import re
import os
import socket
from threading import Thread
from flask import Flask

TOKEN = os.environ['DISCORD_TOKEN']

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print("------")

@bot.tree.command(name="merge", description="FileIDを指定してDiscord上のパーツを結合します")
@app_commands.describe(file_id="結合したいファイルのFileID")
async def merge(interaction: discord.Interaction, file_id: str):
    await interaction.response.send_message(f'🔍 FileID `{file_id}` のパーツを検索中...', ephemeral=True)
    channel = interaction.channel
    messages = []

    async for msg in channel.history(limit=500):
        if file_id in msg.content and msg.attachments:
            part_match = re.search(r'Part (\d+)', msg.content)
            if part_match:
                part_number = int(part_match.group(1))
                messages.append((part_number, msg.attachments[0].url, msg.attachments[0].filename))

    if not messages:
        await interaction.followup.send('❌ パーツが見つかりませんでした。FileIDまたはチャンネルを確認してください。', ephemeral=True)
        return

    messages.sort()
    buffer = io.BytesIO()
    filename = messages[0][2].split('.part')[0]  # 元ファイル名推測

    async with aiohttp.ClientSession() as session:
        for part_number, url, _ in messages:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await interaction.followup.send(f'⚠️ パート {part_number} の取得に失敗しました。', ephemeral=True)
                    return
                chunk = await resp.read()
                buffer.write(chunk)

    buffer.seek(0)
    file = discord.File(fp=buffer, filename=filename)
    await interaction.followup.send(f'✅ 結合完了！ファイル `{filename}` を送信します：', file=file)

@bot.tree.command(name="list", description="チャンネル内で使用されたFileIDの一覧を表示")
async def list_file_ids(interaction: discord.Interaction):
    channel = interaction.channel
    file_ids = set()
    async for msg in channel.history(limit=500):
        match = re.search(r'FileID: (\d+)', msg.content)
        if match:
            file_ids.add(match.group(1))
    if not file_ids:
        await interaction.response.send_message("📂 FileIDは見つかりませんでした。", ephemeral=True)
    else:
        result = "\n".join(f"- {fid}" for fid in sorted(file_ids))
        await interaction.response.send_message(f"📁 このチャンネルにあるFileID一覧:\n{result}", ephemeral=True)

@bot.tree.command(name="ping", description="Botが応答しているか確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! I'm alive.", ephemeral=True)

@bot.tree.command(name="help", description="Botの使い方を表示")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "📘 **SplitMerge Bot 使い方**\n"
        "/merge file_id:<ID> - 指定のFileIDでパーツを結合して送信します\n"
        "/list - チャンネル内のFileID一覧を表示します\n"
        "/ping - Botが生きているか確認します\n"
        "/help - この説明を表示します"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# Flask keep_alive with port reuse check
app = Flask('')

@app.route('/')
def home():
    return 'Bot is alive!'

def keep_alive():
    def run():
        try:
            app.run(host='0.0.0.0', port=8080)
        except OSError:
            print("⚠️ Flaskサーバーのポート 8080 はすでに使用中です。再起動中の可能性があります。")
    Thread(target=run).start()

keep_alive()
bot.run(TOKEN)
