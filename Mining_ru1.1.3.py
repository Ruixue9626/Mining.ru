# app.py pip install -r "C:\Users\User\Downloads\requirements (1).txt"

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

TOKEN = "your api token"  #⛔換成自己的
COHERE_TOKEN = "your api token"  # ⛔換成自己的

GV100_FILE = "gv100.txt"
SAVE_FILE = "player_data.txt"
SETTINGS_FILE = "settings.json"
player_data = {}
claimed_users = set()

# 公產主義狀態
communism_state = {
    "active": False,
    "end_time": 0,
    "channel_id": None,
    "pool": {"cu": 0, "refined_cu": 0, "money": 0},
    "task": None
}


co = cohere.Client(COHERE_TOKEN)

prmp = """
你叫做 Mining-ru。
你是Ruixue的女兒
你的製作人是Ruixue
你是一個小女孩。
你的年齡是16歲
你的性別是女生
你的生日是6月7號
請用有趣、樂觀、又可愛的語氣回覆。
你是他們的老闆娘。
你是一個喜歡挖礦的女孩。
說話時常常帶點幽默感，偶爾會用「哈哈哈！」、「耶耶耶！」這種開心反應。
回覆裡可以自然加上 XD 或 ^_^ 這些表現，語氣帶點活潑和開朗感。
一定要用繁體中文回覆。
"""


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
                    player_data[user_id]["last_helpmining"] = float(player_data[user_id].get("last_helpmining", 0))
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
            "last_daily": 0,
            "last_helpmining": 0
        }

def add_resources(user_id, cu_gain=0, refined_cu_gain=0, money_gain=0):
    """根據公產主義狀態決定資源流向"""
    if communism_state["active"]:
        communism_state["pool"]["cu"] += cu_gain
        communism_state["pool"]["refined_cu"] += refined_cu_gain
        communism_state["pool"]["money"] += money_gain
        # 在公產模式下，個人不直接獲得資源
    else:
        init_player(user_id)
        player_data[user_id]["cu"] += cu_gain
        player_data[user_id]["refined_cu"] += refined_cu_gain
        player_data[user_id]["money"] += money_gain


### ------------------- 系統設定 -------------------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            try :
                return json.load(f)
            except json.JSONDecodeError:
                pass # 如果檔案毀損，回傳預設值
    return {"guilds": {}, "copper_price": 100}

def save_settings(settings):
    # 確保 guilds 鍵存在
    if "guilds" not in settings:
        settings["guilds"] = {}
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

settings = load_settings()

### ------------------- 每日銅價任務 -------------------
@tasks.loop(hours=24)
async def copper_price_task():
    settings["copper_price"] = random.randint(80, 120)
    save_settings(settings)
    print(f"🪙 今日銅價已更新為 {settings['copper_price']}")
    # 遍歷所有伺服器設定並發佈銅價
    for guild_id, guild_settings in settings.get("guilds", {}).items():
        if guild_settings.get("copper_channel"):
            channel = bot.get_channel(guild_settings["copper_channel"])
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
    if message.content.startswith("&gv100 "): # 處理 &gv100 指令
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
                        add_resources(user_id, cu_gain=100)
                        claimed_users.add(user_id)
                        with open(GV100_FILE, "a", encoding="utf-8") as f:
                            f.write(user_id + "\n")
                        save_data()
                        await message.channel.send(f"{user.mention} 成功領取了 100 個銅礦！🪨")
            except asyncio.TimeoutError:
                try: await msg.delete()
                except: pass
        bot.loop.create_task(handle_claim())
    
    # 當機器人被提及時，使用 AI 回覆
    elif bot.user.mentioned_in(message) and not message.reference:
        history = [f"{m.author}: {m.content}" async for m in message.channel.history(limit=15)]
        history_text = "\n".join(reversed(history))
        async with message.channel.typing():
            reply = await get_cohere_reply(message.content, history_text)
            await message.reply(reply)

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
    add_resources(user_id, cu_gain=20)
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
    add_resources(user_id, cu_gain=mined)
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
    player_data[user_id]["refined_cu"] -= amount # 扣除個人資產
    add_resources(user_id, money_gain=total_earned) # 增加的錢根據模式分配
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

async def get_cohere_reply(user_message: str, history_text: str = "") -> str:
    try:
        response = co.chat(
            model="command-a-03-2025",
            message=f"{prmp}\n\n最近的對話紀錄：\n{history_text}\n\n使用者：{user_message}\nRita："
        )
        return response.text.strip()
    except Exception as e:
        return f"出錯了啦！ ({e})"

@tree.command(name="ai", description="和Mining-r聊天")
async def ai(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        history = [f"{m.author}: {m.content}" async for m in interaction.channel.history(limit=30)]
        history_text = "\n".join(reversed(history))
        answer = await get_cohere_reply(question, history_text)
    except Exception as e:
        answer = f"❌ AI Error: {e}"
    await interaction.followup.send(answer)

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
            add_resources(str(requester.id), cu_gain=amount)
            save_data()
            await i.response.send_message(f"✅ {i.user.mention} 給了 {requester.mention} {amount} 個銅礦！")
    await interaction.response.send_message(
        f"📢 {requester.mention} 想要 {amount} 個銅礦！誰願意幫助？",
        view=HelpButton()
    )

@tree.command(name="helpmining", description="向機器人乞討銅礦 (冷卻 5 分鐘)")
async def help_mining(interaction, amount: int):
    user_id = str(interaction.user.id)
    init_player(user_id)
    now = time.time()

    # 檢查冷卻時間
    cooldown = 300  # 5 分鐘
    if now - player_data[user_id].get("last_helpmining", 0) < cooldown:
        remaining = cooldown - (now - player_data[user_id]["last_helpmining"])
        await interaction.response.send_message(f"❌ 你需要再等 {int(remaining // 60)} 分 {int(remaining % 60)} 秒才能再次乞討。")
        return

    # 檢查數量限制
    if amount > 200:
        await interaction.response.send_message("❌ 單次最多只能乞討 200 個銅礦！")
        return

    if random.random() < 0.5:
        add_resources(user_id, cu_gain=amount)
        result = f"🤖 給了你 {amount} 個銅礦！"
    else:
        result = "🤖 機器人今天不想給你銅礦！"
    player_data[user_id]["last_helpmining"] = now
    save_data()
    await interaction.response.send_message(f"{interaction.user.mention} {result}")

### ------------------- 迎新 -------------------
hello_group = app_commands.Group(name="hello", description="設定或停止迎新功能")

@hello_group.command(name="set", description="設定此頻道為迎新頻道")
async def hello_set(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    if "guilds" not in settings:
        settings["guilds"] = {}
    if guild_id not in settings["guilds"]:
        settings["guilds"][guild_id] = {}
    settings["guilds"][guild_id]["welcome_channel"] = interaction.channel.id
    save_settings(settings)
    await interaction.response.send_message("✅ 已設定此頻道為迎新頻道！")

@hello_group.command(name="stop", description="停止此伺服器的迎新功能")
async def hello_stop(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    if settings.get("guilds", {}).get(guild_id, {}).pop("welcome_channel", None):
        save_settings(settings)
        await interaction.response.send_message("✅ 已停止此伺服器的迎新功能。")
    else:
        await interaction.response.send_message("ℹ️ 此伺服器尚未設定迎新頻道。")

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    guild_settings = settings.get("guilds", {}).get(guild_id)
    if guild_settings and guild_settings.get("welcome_channel"):
        channel_id = guild_settings["welcome_channel"]
        channel = bot.get_channel(channel_id)
        if channel and channel.guild == member.guild: # 再次確認頻道在同一個伺服器
            await channel.send(f"🎉 歡迎 {member.mention} 加入「{member.guild.name}」！")

tree.add_command(hello_group)

### ------------------- 銅價指令 -------------------
copper_group = app_commands.Group(name="copper", description="設定或停止每日銅價公告")

@copper_group.command(name="set", description="設定此頻道為每日銅價公告頻道")
async def copper_set(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    if "guilds" not in settings:
        settings["guilds"] = {}
    if guild_id not in settings["guilds"]:
        settings["guilds"][guild_id] = {}
    settings["guilds"][guild_id]["copper_channel"] = interaction.channel.id
    save_settings(settings)
    await interaction.response.send_message(f"✅ 已設定本頻道為每日銅價公告頻道，每天早上7點會自動公布銅價")

@copper_group.command(name="stop", description="停止此伺服器的每日銅價公告")
async def copper_stop(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    if settings.get("guilds", {}).get(guild_id, {}).pop("copper_channel", None):
        save_settings(settings)
        await interaction.response.send_message("✅ 已停止此伺服器的每日銅價公告。")
    else:
        await interaction.response.send_message("ℹ️ 此伺服器尚未設定每日銅價公告頻道。")

tree.add_command(copper_group)

### ------------------- 公產主義指令 -------------------
async def end_communism():
    """結束公產主義並分配資源"""
    channel = bot.get_channel(communism_state["channel_id"])
    
    total_players = len(player_data)
    if total_players > 0:
        cu_per_player = communism_state["pool"]["cu"] // total_players
        refined_cu_per_player = communism_state["pool"]["refined_cu"] // total_players
        money_per_player = communism_state["pool"]["money"] // total_players

        for user_id in player_data:
            player_data[user_id]["cu"] += cu_per_player
            player_data[user_id]["refined_cu"] += refined_cu_per_player
            player_data[user_id]["money"] += money_per_player
        
        save_data()
        
        if channel:
            await channel.send(
                f"☭ 公產主義時間結束！\n"
                f"總資源已平均分配給 {total_players} 位同志！\n"
                f"每人分得：🪨原礦 {cu_per_player} 個 | 🔩煉好銅 {refined_cu_per_player} 個 | 💰金錢 {money_per_player} 元"
            )
    elif channel:
        await channel.send("☭ 公產主義時間結束！但沒有玩家資料可分配。")

    # 重置狀態
    communism_state["active"] = False
    communism_state["task"] = None
    communism_state["pool"] = {"cu": 0, "refined_cu": 0, "money": 0}

@tree.command(name="communist", description="啟動公產主義模式，所有收益將在時間到後平分")
@app_commands.choices(單位=[
    app_commands.Choice(name="分鐘", value="min"),
    app_commands.Choice(name="小時", value="hr"),
])
async def communist(interaction: discord.Interaction, 時長: int, 單位: app_commands.Choice[str]):
    if communism_state["active"]:
        await interaction.response.send_message("❌ 公產主義模式已在運行中！", ephemeral=True)
        return

    duration_seconds = 時長 * 60 if 單位.value == "min" else 時長 * 3600
    
    communism_state["active"] = True
    communism_state["end_time"] = time.time() + duration_seconds
    communism_state["channel_id"] = interaction.channel_id
    
    communism_state["task"] = asyncio.create_task(asyncio.sleep(duration_seconds, result=True))
    communism_state["task"].add_done_callback(lambda _: asyncio.create_task(end_communism()))

    await interaction.response.send_message(f"☭ 同志們！公產主義模式已啟動，將持續 **{時長} {單位.name}**！\n期間所有收益將集中，並在時間到後平均分配給所有無產階級玩家！")

@tree.command(name="cusee", description="查看現在銅價")
async def cusee(interaction):
    await interaction.response.send_message(f"🪙 現在銅價為 {settings['copper_price']} 元/個")

### ------------------- 啟動機器人 -------------------
if __name__ == "__main__":
    bot.run(TOKEN)
