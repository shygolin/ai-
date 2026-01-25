import discord
from discord.ext import commands
from discord import app_commands
from config import DISCORD_TOKEN
from local_engine import BpmfEngine
from bpmf_converter import is_bopomofo_scramble
from bpmf_segmenter import segment_ascii

# 1. 初始化引擎
engine = BpmfEngine('weighted_dict.json')

# 2. 設定機器人 (Prefix 用於同步指令，Intents 開啟所有權限)
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"--------------------------------")
    print(f"✅ 機器人 {bot.user} 已上線")
    print(f"✅ 輸入 !synccommands 來啟用斜線指令")
    print(f"--------------------------------")

# --- 同步指令：將寫好的 Slash Command 傳送到 Discord 伺服器 ---
@bot.command()
async def synccommands(ctx):
    try:
        # 同步此機器人所有的 tree command
        synced = await bot.tree.sync()
        await ctx.send(f"♻️ 已同步 {len(synced)} 個斜線指令！(請稍候片刻讓 Discord 更新)")
    except Exception as e:
        await ctx.send(f"❌ 同步失敗: {e}")

# --- 斜線指令：手動新增詞庫 (/add) ---
@bot.tree.command(name="add", description="手動教機器人新的注音對應字詞")
@app_commands.describe(word="想要顯示的中文 (例: 大帥哥)", bpmf="對應的注音 (例: ㄉㄚˋ ㄕㄨㄞˋ ㄍㄜ)")
async def add(interaction: discord.Interaction, word: str, bpmf: str):
    success = engine.add_word(word, bpmf)
    if success:
        await interaction.response.send_message(f"🧠 學習成功！現在 `{bpmf}` 會優先轉換為 `{word}`")
    else:
        await interaction.response.send_message(f"⚠️ 儲存失敗。可能是該詞已存在，或格式有誤。")

# --- 主要監聽邏輯 ---
@bot.event
async def on_message(message):
    # 忽略機器人自己的訊息
    if message.author == bot.user:
        return

    # 重要：確保普通指令 (!開頭的) 能運作
    await bot.process_commands(message)

    content = message.content.strip()

    # 偵測是否為注音亂碼
    if is_bopomofo_scramble(content) and len(content) >= 2:
        # A. 切分注音
        _, bopomofo_segs = segment_ascii(content)
        
        # B. 透過引擎轉換成中文
        final_text = engine.convert(bopomofo_segs)
        
        # C. 回覆結果
        await message.reply(f"🔍 亂碼翻譯：**{final_text}**")

bot.run(DISCORD_TOKEN)