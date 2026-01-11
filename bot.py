import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
import subprocess
import os
from dotenv import load_dotenv
from asyncio import Queue
import time

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents.default())
queue = []
is_loop = False

TOKEN = ('MTQ1NDcwNzQzODI0MTcxMDIxNw.Gx7TIW.PAy5PUMocaOWs6kqOx-_zmbvHtL5Ewn6XgfzIo')
music_queues = {}  # guild_id -> [url, ...]
loop_status = {}   # guild_id -> True/False
stop_flag = {}     # guild_id -> True/False

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"{len(synced)} command(s) synced")
    print("Bot online")
    cmds = [c.name for c in bot.tree.get_commands()]
    print("Commands:", cmds)

@bot.tree.command(name="stop", description="หยุดเพลงทั้งหมด")
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    # เช็กว่าบอทอยู่ใน voice channel
    if vc and vc.is_connected():
        stop_flag[guild_id] = True       # ตั้ง flag เพื่อให้ play_next หยุดเล่นเพลงต่อ
        music_queues[guild_id] = []      # ล้าง queue
        vc.stop()                        # หยุดเพลงปัจจุบัน
        await interaction.response.send_message("หยุดเพลงแล้ว! ✅")
    else:
        await interaction.response.send_message("ไม่มีเพลงกำลังเล่น!", ephemeral=True)


@bot.tree.command(name="play", description="เปิดเพลงจาก YouTube")
@app_commands.describe(url="ลิงก์ ")
async def play(interaction: discord.Interaction, url: str):
    global last_url
    last_url = url
    await interaction.response.send_message("⏳ กำลังโหลดเพลง...")
    await handle_play(interaction, url)
async def handle_play(interaction: discord.Interaction, url: str):
    

    async def player():
        try:
            if interaction.user.voice is None:
                await interaction.edit_original_response(
                    content="❌ คุณยังไม่ได้เข้าห้อง"
                )
                return

            voice = discord.utils.get(bot.voice_clients, guild=interaction.guild)
            if voice is None:
                voice = await interaction.user.voice.channel.connect()

            ydl_opts = {
                "format": "bestaudio",
                "noplaylist": True,
                "quiet": True,
            }

            loop = asyncio.get_running_loop()

            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await loop.run_in_executor(None, extract)

            audio_url = info["url"]
            title = info.get("title", "ไม่ทราบชื่อเพลง")

            if voice.is_playing():
                voice.stop()

            source = discord.FFmpegPCMAudio(
                audio_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn",
            )

            voice.play(source)

            await interaction.edit_original_response(
                content=f"🎶 กำลังเล่น: **{title}**"
            )

        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ Error\n```{e}```"
            )

    # ⭐ สำคัญที่สุด: รันเบื้องหลัง
    asyncio.create_task(player())

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    text = message.content.lower()

    if "สวัสดี" in text:
        await message.channel.send("สวัสดีครับ 😄")
    elif "ชื่ออะไร" in text:
        await message.channel.send("ผมคือ Chatbot ครับ")
    elif "ทำอะไรได้" in text:
        await message.channel.send("ผมคุยกับคุณได้ 😆")
    else:
        await message.channel.send("ผมยังไม่เข้าใจครับ")

        await interaction.response.defer()


@bot.tree.command(name='hellobot', description='replies with Hello')
async def hellocommand(interaction):
    await interaction.response.send_message("Hello")

@bot.command()
async def test(ctx, *, arg):
    await ctx.send(arg)


@bot.tree.command(name="loop", description="เปิด/ปิด โหมดเล่นซ้ำ")
async def loop_command(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    current_status = loop_status.get(guild_id, False)
    loop_status[guild_id] = not current_status

    status_text = "เปิด" if loop_status[guild_id] else "ปิด"
    await interaction.response.send_message(f"🔁 โหมดเล่นซ้ำ: {status_text}")

async def play_next(guild_id, voice):
    while True:
        if stop_flag.get(guild_id, False):
            break

        if not music_queues.get(guild_id):
            break

        url = music_queues[guild_id].pop(0)

        ydl_opts = {
            "format": "bestaudio",
            "noplaylist": True,
            "quiet": True,
        }

        loop = asyncio.get_running_loop()

        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        info = await loop.run_in_executor(None, extract)

        audio_url = info["url"]
        title = info.get("title", "ไม่ทราบชื่อเพลง")

        source = discord.FFmpegPCMAudio(
            audio_url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn",
        )

        voice.play(source)

        while voice.is_playing() or voice.is_paused():
            await asyncio.sleep(1)

        if loop_status.get(guild_id, False):
            music_queues[guild_id].append(url)
async def handle_play(interaction: discord.Interaction, url: str):
    guild_id = interaction.guild.id

    if guild_id not in music_queues:
        music_queues[guild_id] = []

    music_queues[guild_id].append(url)

    voice = interaction.guild.voice_client
    if not voice:
        voice = await interaction.user.voice.channel.connect()

    if not voice.is_playing():
        asyncio.create_task(play_next(guild_id, voice))






bot.run(os.getenv('MTQ1NDcwNzQzODI0MTcxMDIxNw.Gx7TIW.PAy5PUMocaOWs6kqOx-_zmbvHtL5Ewn6XgfzIo'))  
