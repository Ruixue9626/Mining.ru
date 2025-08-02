
# app.py

import discord
from discord import app_commands
import random
import time
import json
import os
import subprocess
import asyncio
import cohere
TOKEN = "Discord bot api"  # ⛔請換成你自己的
COHERE_TOKEN = "cohere api"  # ⛔請換成你自己的

GV100_FILE = "gv100.txt"
SAVE_FILE = "player_data.txt"
player_data = {}
claimed_users = set()

co = cohere.Client(COHERE_TOKEN)

intents = discord.Intents.all()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

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

@bot.event
async def on_ready():
    load_data()
    await tree.sync()
    print(f'機器人已上線！登入為 {bot.user.name}')

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
            return (
                str(reaction.emoji) == "✅"
                and reaction.message.id == msg.id
                and not user.bot
            )

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
                try:
                    await msg.delete()
                except:
                    pass

        bot.loop.create_task(handle_claim())

    await tree.process_commands(message)

@tree.command(name="hi", description="跟機器人打招呼！")
async def hi(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hi~ {interaction.user.mention} 👋")

@tree.command(name="daily", description="每日簽到獎勵 20 個銅礦原礦")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    init_player(user_id)
    now = time.time()
    last_daily = player_data[user_id].get("last_daily", 0)
    if now - last_daily < 86400:
        await interaction.response.send_message("你今天已經簽到過了，請明天再來！")
        return
    player_data[user_id]["cu"] += 20
    player_data[user_id]["last_daily"] = now
    save_data()
    await interaction.response.send_message(f"{interaction.user.mention} 簽到成功！獲得 20 個原礦 🪨")

@tree.command(name="cu", description="挖銅礦")
@app_commands.describe(member="要幫誰挖？留空為自己")
async def cu(interaction: discord.Interaction, member: discord.Member = None):
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
@app_commands.describe(amount="要煉幾個")
async def fire(interaction: discord.Interaction, amount: int):
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

@tree.command(name="sell", description="販售煉銅")
@app_commands.describe(amount="要賣幾個", price="單價")
async def sell(interaction: discord.Interaction, amount: int, price: int):
    user_id = str(interaction.user.id)
    init_player(user_id)

    if amount <= 0 or price <= 0:
        await interaction.response.send_message("數量與價格必須大於 0。")
        return

    if amount > player_data[user_id]["refined_cu"]:
        await interaction.response.send_message("你沒有足夠的煉好銅可以出售。")
        return

    total_earned = amount * price
    player_data[user_id]["refined_cu"] -= amount
    player_data[user_id]["money"] += total_earned
    save_data()
    await interaction.response.send_message(
        f"{interaction.user.mention} 賣出了 {amount} 個煉好銅，獲得 {total_earned} 元！\n"
        f"剩餘煉好銅：{player_data[user_id]['refined_cu']} 個，總資金：{player_data[user_id]['money']} 元。"
    )

@tree.command(name="see", description="查看玩家狀態")
@app_commands.describe(member="要查看的對象")
async def see(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    user_id = str(target.id)
    init_player(user_id)
    cu = player_data[user_id]["cu"]
    refined = player_data[user_id]["refined_cu"]
    money = player_data[user_id]["money"]
    await interaction.response.send_message(f"{target.mention} 擁有：\n🪨 原礦：{cu} 個\n🔩 煉好銅：{refined} 個\n💰 金錢：{money} 元")

@tree.command(name="say", description="讓機器人幫你說話")
@app_commands.describe(message="你想說什麼？")
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message)

@tree.command(name="yt", description="使用 yt-dlp 下載 YouTube 影片")
@app_commands.describe(url="YouTube 影片連結")
async def yt(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    try:
        filename = "yt_video.mp4"
        command = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", filename, url]
        subprocess.run(command, check=True)
        await interaction.followup.send(content="🎬 成功下載影片！", file=discord.File(filename))
        os.remove(filename)
    except Exception as e:
        await interaction.followup.send(f"❌ I am sorry發生錯誤：{e}")

@tree.command(name="ai", description="使用 AI 問問題")
@app_commands.describe(message="你想問的問題")
async def ai(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    try:
        response = co.generate(model='command-r-plus-08-2024', prompt=message, max_tokens=100)
        if response.generations:
            await interaction.followup.send(response.generations[0].text.strip())
        else:
            await interaction.followup.send("❌I am sorry AI 未能產生回應")
    except Exception as e:
        await interaction.followup.send(f"❌I am sorry AI 回答失敗：{str(e)}")

@tree.command(name="gift", description="送禮物給別人，可選類型：&Cu / &Fcu / &Money")
@app_commands.describe(
    kind="&Cu 原礦 / &Fcu 煉銅 / &Money 金錢",
    member="要送禮的人",
    amount="數量"
)
async def gift(interaction: discord.Interaction, kind: str, member: discord.Member, amount: int):
    giver = str(interaction.user.id)
    receiver = str(member.id)
    init_player(giver)
    init_player(receiver)

    if amount <= 0:
        await interaction.response.send_message("送的數量要大於 0 喔~")
        return

    if kind == "&Cu":
        if player_data[giver]["cu"] < amount:
            await interaction.response.send_message("你的原礦不夠喔！")
            return
        player_data[giver]["cu"] -= amount
        player_data[receiver]["cu"] += amount
        await interaction.response.send_message(f"{interaction.user.mention} 送出了 {amount} 個原礦給 {member.mention} 🎁")

    elif kind == "&Fcu":
        if player_data[giver]["refined_cu"] < amount:
            await interaction.response.send_message("你的煉銅不夠喔！")
            return
        player_data[giver]["refined_cu"] -= amount
        player_data[receiver]["refined_cu"] += amount
        await interaction.response.send_message(f"{interaction.user.mention} 送出了 {amount} 個煉好的銅給 {member.mention} 🎁")

    elif kind == "&Money":
        if player_data[giver]["money"] < amount:
            await interaction.response.send_message("你沒那麼多錢啦 QQ")
            return
        player_data[giver]["money"] -= amount
        player_data[receiver]["money"] += amount
        await interaction.response.send_message(f"{interaction.user.mention} 送出了 {amount} 元給 {member.mention} 💸")

    else:
        await interaction.response.send_message("未知的類型喔～請用 &Cu / &Fcu / &Money 其中一種！")

bot.run(TOKEN)
