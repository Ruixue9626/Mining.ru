# app.py

import discord
from discord import app_commands
from discord.ext import tasks
import random
import time
import json
import os
import subprocess
import asyncio
import cohere
import datetime

TOKEN = "your api kay"  #⛔換成自己的
COHERE_TOKEN = "your api kay"  # ⛔換成自己的

GV100_FILE = "gv100.txt"
SAVE_FILE = "player_data.txt"
SETTINGS_FILE = "settings.json"
player_data = {}
claimed_users = set()

co = cohere.Client(COHERE_TOKEN)

intents = discord.Intents.all()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

### ------------------- 玩家資料 -------------------
def load_data():
    global player_data
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            try:
                player_data = json.load(f)
                for user_id in player_data:
                    player_data[user_id]["last_cu"] = float(player_data[user_id].get("last_cu", 0))
                    player_data[user_id]["last_fire"] = float(player_data[user_id].get("last_fire", 0))
                    player_data[user_id]["last_daily"] = float(player_data[user_id].get("last_daily", 0))
            except json.JSONDecodeError:
                player_data = {}

    if os.path.exists(GV100_FILE):
        with open(GV100_FILE, "r", encoding="utf-8") as f:
            global claimed_users
            claimed_users = set(f.read().splitlines())

def save_data():
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(player_data, f, ensure_ascii=False, indent=2)

def init_player(user_id):
    if str(user_id) not in player_data:
        player_data[str(user_id)] = {
            "cu": 0,
            "refined_cu": 0,
            "money": 0,
            "last_cu": 0,
            "last_fire": 0,
            "last_daily": 0
        }

### ------------------- 系統設定 -------------------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"welcome_channel": None, "copper_channel": None, "copper_price": 100}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

settings = load_settings()

### ------------------- 每日銅價任務 -------------------
@tasks.loop(hours=24)
async def copper_price_task():
    settings["copper_price"] = random.randint(80, 120)
    save_settings(settings)
    print(f"🪙 今日銅價已更新為 {settings['copper_price']}")
    # 發佈銅價到指定頻道
    if settings.get("copper_channel"):
        channel = bot.get_channel(settings["copper_channel"])
        if channel:
            await channel.send(f"🪙 今日銅價為 {settings['copper_price']} 元/個")

@bot.event
async def on_ready():
    load_data()
    await tree.sync()
    copper_price_task.start()
    print(f'✅ 機器人已上線！登入為 {bot.user.name}')

### ------------------- 特殊領礦 gv100 -------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.startswith("&gv100 "):
        parts = message.content.split()
        if len(parts) != 2 or parts[1] != "000325":
            await message.channel.send("❌ 密碼錯誤！")
            return

        msg = await message.channel.send("🎁 點擊 ✅ 領取 100 個銅礦！")
        await msg.add_reaction("✅")

        def check(reaction, user):
            return str(reaction.emoji) == "✅" and reaction.message.id == msg.id and not user.bot

        async def handle_claim():
            try:
                while True:
                    reaction, user = await bot.wait_for("reaction_add", timeout=86400, check=check)
                    user_id = str(user.id)
                    if user_id in claimed_users:
                        await message.channel.send(f"{user.mention} 你已經領取過了！")
                    else:
                        init_player(user_id)
                        player_data[user_id]["cu"] += 100
                        claimed_users.add(user_id)
                        with open(GV100_FILE, "a", encoding="utf-8") as f:
                            f.write(user_id + "\n")
                        save_data()
                        await message.channel.send(f"{user.mention} 成功領取了 100 個銅礦！🪨")
            except asyncio.TimeoutError:
                try: await msg.delete()
                except: pass
        bot.loop.create_task(handle_claim())
    await tree.process_commands(message)

### ------------------- 遊戲指令 -------------------
@tree.command(name="hi", description="跟機器人打招呼！")
async def hi(interaction):
    await interaction.response.send_message(f"Hi~ {interaction.user.mention} 👋")

@tree.command(name="daily", description="每日簽到獎勵 20 個銅礦原礦")
async def daily(interaction):
    user_id = str(interaction.user.id)
    init_player(user_id)
    now = time.time()
    if now - player_data[user_id]["last_daily"] < 86400:
        await interaction.response.send_message("你今天已經簽到過了，請明天再來！")
        return
    player_data[user_id]["cu"] += 20
    player_data[user_id]["last_daily"] = now
    save_data()
    await interaction.response.send_message(f"{interaction.user.mention} 簽到成功！獲得 20 個原礦 🪨")

@tree.command(name="cu", description="挖銅礦")
async def cu(interaction, member: discord.Member = None):
    target = member or interaction.user
    user_id = str(target.id)
    init_player(user_id)
    now = time.time()
    if now - player_data[user_id]["last_cu"] < 5:
        await interaction.response.send_message("你過勞了！")
        return
    mined = random.randint(1, 10)
    player_data[user_id]["cu"] += mined
    player_data[user_id]["last_cu"] = now
    save_data()
    await interaction.response.send_message(f"{interaction.user.mention} 挖到了 {mined} 個銅礦原礦！")

@tree.command(name="fire", description="煉銅礦")
async def fire(interaction, amount: int):
    user_id = str(interaction.user.id)
    init_player(user_id)
    now = time.time()
    if now - player_data[user_id]["last_fire"] < 10:
        await interaction.response.send_message("你過勞了！")
        return
    if amount <= 0 or amount > player_data[user_id]["cu"]:
        await interaction.response.send_message("數量錯誤或原礦不足")
        return
    player_data[user_id]["cu"] -= amount
    player_data[user_id]["refined_cu"] += amount
    player_data[user_id]["last_fire"] = now
    save_data()
    await interaction.response.send_message(f"{interaction.user.mention} 成功煉製了 {amount} 個銅礦")

@tree.command(name="sell", description="以今日銅價販售煉銅")
async def sell(interaction, amount: int):
    user_id = str(interaction.user.id)
    init_player(user_id)
    if amount <= 0:
        await interaction.response.send_message("數量必須大於 0。")
        return
    if amount > player_data[user_id]["refined_cu"]:
        await interaction.response.send_message("你沒有足夠的煉好銅可以出售。")
        return
    price = settings["copper_price"]
    total_earned = amount * price
    player_data[user_id]["refined_cu"] -= amount
    player_data[user_id]["money"] += total_earned
    save_data()
    await interaction.response.send_message(
        f"{interaction.user.mention} 以今日銅價 {price}/個 賣出了 {amount} 個煉好銅，獲得 {total_earned} 元！"
    )

@tree.command(name="see", description="查看玩家狀態")
async def see(interaction, member: discord.Member = None):
    target = member or interaction.user
    user_id = str(target.id)
    init_player(user_id)
    cu, refined, money = player_data[user_id]["cu"], player_data[user_id]["refined_cu"], player_data[user_id]["money"]
    await interaction.response.send_message(f"{target.mention} 擁有：🪨原礦 {cu} 個 | 🔩煉好銅 {refined} 個 | 💰金錢 {money} 元")

### ------------------- 語音/AI/YouTube -------------------
@tree.command(name="say", description="讓機器人幫你說話")
async def say(interaction, message: str):
    await interaction.response.send_message(message)

@tree.command(name="yt", description="使用 yt-dlp 下載 YouTube 影片")
async def yt(interaction, url: str):
    await interaction.response.defer(thinking=True)
    try:
        filename = "yt_video.mp4"
        command = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", filename, url]
        subprocess.run(command, check=True)
        if os.path.exists(filename):
            await interaction.followup.send(content="🎬 成功下載影片！", file=discord.File(filename))
            os.remove(filename)
        else:
            await interaction.followup.send("❌ 影片下載失敗！")
    except Exception as e:
        await interaction.followup.send(f"❌ 下載錯誤：{e}")

@tree.command(name="ai", description="使用 AI 問問題")
async def ai(interaction, message: str):
    await interaction.response.defer(thinking=True)
    try:
        response = co.generate(model='command-r-plus-08-2024', prompt=message, max_tokens=100)
        if response.generations:
            await interaction.followup.send(response.generations[0].text.strip())
        else:
            await interaction.followup.send("❌ AI 未能產生回應")
    except Exception as e:
        await interaction.followup.send(f"❌ AI 回答失敗：{str(e)}")

### ------------------- 玩家乞討 -------------------
@tree.command(name="help", description="向其他玩家乞討銅礦")
async def help_cmd(interaction, amount: int):
    requester = interaction.user
    class HelpButton(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
        @discord.ui.button(label="💰 施捨", style=discord.ButtonStyle.green)
        async def give(self, i: discord.Interaction, b: discord.ui.Button):
            giver_id = str(i.user.id)
            init_player(giver_id)
            if player_data[giver_id]["cu"] < amount:
                await i.response.send_message("❌ 你沒有足夠的銅礦！", ephemeral=True)
                return
            player_data[giver_id]["cu"] -= amount
            init_player(str(requester.id))
            player_data[str(requester.id)]["cu"] += amount
            save_data()
            await i.response.send_message(f"✅ {i.user.mention} 給了 {requester.mention} {amount} 個銅礦！")
    await interaction.response.send_message(
        f"📢 {requester.mention} 想要 {amount} 個銅礦！誰願意幫助？",
        view=HelpButton()
    )

@tree.command(name="helpmining", description="向機器人乞討")
async def help_mining(interaction, amount: int):
    user_id = str(interaction.user.id)
    init_player(user_id)
    if random.random() < 0.5:
        player_data[user_id]["cu"] += amount
        result = f"🤖 給了你 {amount} 個銅礦！"
    else:
        player_data[user_id]["money"] += 20
        result = "🤖 沒有銅礦！但給了你 20 元！"
    save_data()
    await interaction.response.send_message(f"{interaction.user.mention} {result}")

### ------------------- 迎新 -------------------
@tree.command(name="hello", description="設定迎新頻道")
async def hello_cmd(interaction):
    settings["welcome_channel"] = interaction.channel.id
    save_settings(settings)
    await interaction.response.send_message("✅ 已設定此頻道為迎新頻道！")

@bot.event
async def on_member_join(member):
    if settings.get("welcome_channel"):
        channel = bot.get_channel(settings["welcome_channel"])
        if channel:
            await channel.send(f"🎉 歡迎 {member.mention} 加入伺服器！")

### ------------------- 新增銅價指令 -------------------
@tree.command(name="cunow", description="設定本頻道為每日銅價公告頻道")
async def cunow(interaction):
    settings["copper_channel"] = interaction.channel.id
    save_settings(settings)
    await interaction.response.send_message(f"✅ 已設定本頻道為每日銅價公告頻道，每天早上7點會自動公布銅價")

@tree.command(name="cusee", description="查看現在銅價")
async def cusee(interaction):
    await interaction.response.send_message(f"🪙 現在銅價為 {settings['copper_price']} 元/個")

### ------------------- 啟動機器人 -------------------
if __name__ == "__main__":
    bot.run(TOKEN)
