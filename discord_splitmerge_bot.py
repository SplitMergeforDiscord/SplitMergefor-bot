import discord
from discord.ext import commands
import aiohttp
import io
import re

TOKEN = 'YOUR_BOT_TOKEN_HERE'  # ← あなたのBotトークンをここに

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command()
async def merge(ctx, file_id: str):
    await ctx.send(f'🔍 FileID `{file_id}` のパーツを検索中...')

    messages = []
    async for msg in ctx.channel.history(limit=500):
        if file_id in msg.content and msg.attachments:
            part_match = re.search(r'Part (\d+)', msg.content)
            if part_match:
                part_number = int(part_match.group(1))
                messages.append((part_number, msg.attachments[0].url, msg.attachments[0].filename))

    if not messages:
        await ctx.send('❌ パーツが見つかりませんでした。FileIDまたはチャンネルを確認してください。')
        return

    messages.sort()
    buffer = io.BytesIO()
    filename = messages[0][2].split('.part')[0]  # 元ファイル名推測

    async with aiohttp.ClientSession() as session:
        for part_number, url, _ in messages:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await ctx.send(f'⚠️ パート {part_number} の取得に失敗しました。')
                    return
                chunk = await resp.read()
                buffer.write(chunk)

    buffer.seek(0)
    file = discord.File(fp=buffer, filename=filename)
    await ctx.send(f'✅ 結合完了！ファイル `{filename}` を送信します:', file=file)

bot.run(TOKEN)
