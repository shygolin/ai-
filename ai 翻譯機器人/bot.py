import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import re
from config import DISCORD_TOKEN
from local_engine import BpmfEngine
from bpmf_converter import is_bopomofo_scramble
from bpmf_segmenter import segment_ascii

# 初始化 SQL 引擎
engine = BpmfEngine('dictionary.db')
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"✅ {bot.user} 已上線 (SQL 模式)")

@bot.command()
async def synccommands(ctx):
    await bot.tree.sync()
    await ctx.send("♻️ 指令同步完成")

@bot.tree.command(name="add", description="輸入亂碼與中文，自動進行單字分類")
@app_commands.describe(scramble="亂碼 (例: ru8 cl3)", word="中文)")
async def add(interaction: discord.Interaction, scramble: str, word: str):
    _, bopomofo_segs = segment_ascii(scramble)

    if not bopomofo_segs or len(bopomofo_segs) != len(word):
        await interaction.response.send_message(f"❌ 字數不符！亂碼拆出 {len(bopomofo_segs)} 個音，但你給了 {len(word)} 個字。")
        return

    if engine.add_word(word, bopomofo_segs):
        embed = discord.Embed(
            title="🧠 已學習新詞",
            description=f"之後遇到 `{scramble}` 會翻譯成 {word}",
            color=discord.Color.green()
        )
        embed.add_field(name="亂碼", value=scramble, inline=False)
        embed.add_field(name="對應", value=word, inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"⚠️ 學習失敗。")

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

    content = message.content.strip()
    # 智慧過濾：只有真正的純英文單詞（不含數字）才不翻
    if re.fullmatch(r'[A-Za-z\s]+', content) and not any(char.isdigit() for char in content):
        return

    # 檢查是否在忽略列表中
    if engine.is_ignored(content.lower()):
        return

    if is_bopomofo_scramble(content) and len(content) >= 1:
        _, bopomofo_segs = segment_ascii(content)
        final_text = engine.convert(bopomofo_segs)

        # 只要結果包含中文字就回覆
        if any('\u4e00' <= char <= '\u9fff' for char in final_text):
            embed = discord.Embed(
                title="🔍 翻譯結果",
                color=discord.Color.blue()
            )
            embed.add_field(name="誤輸入", value=content, inline=False)
            embed.add_field(name="實際意思", value=final_text, inline=False)

            view = TranslationView(content, final_text, bopomofo_segs, message.author.id)
            await message.reply(embed=embed, view=view)

# --- 查詢指令：查看某個亂碼底下的候選字 (/check) ---
@bot.tree.command(name="check", description="查詢某個亂碼目前的候選字與權重")
@app_commands.describe(scramble="想要查詢的亂碼 (例: ru8)")
async def check(interaction: discord.Interaction, scramble: str):
    # 先將亂碼轉為注音
    _, bopomofo_segs = segment_ascii(scramble)
    if not bopomofo_segs:
        await interaction.response.send_message(f"❌ 無法辨識亂碼 `{scramble}`")
        return

    bpmf_query = "".join(bopomofo_segs)
    candidates = engine.get_candidates(bpmf_query)

    if not candidates:
        await interaction.response.send_message(f"🔍 字典中找不到關於 `{bpmf_query}` ({scramble}) 的記錄。")
        return

    # 格式化輸出
    embed = discord.Embed(
        title="📖 詞彙查詢",
        color=discord.Color.blue()
    )
    embed.add_field(name="查詢", value=scramble, inline=False)

    candidates_text = ""
    for i, (word, freq) in enumerate(candidates, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        candidates_text += f"{medal} {word} ({freq}分)\n"

    embed.add_field(name="候選字", value=candidates_text, inline=False)
    await interaction.response.send_message(embed=embed)

# --- 刪除指令：忘記錯誤的學習 (/forget) ---
@bot.tree.command(name="forget", description="刪除字典中錯誤的對應關係")
@app_commands.describe(scramble="亂碼 (例: ru8)", word="想要刪除的中文 (例: 假)")
async def forget(interaction: discord.Interaction, scramble: str, word: str):
    _, bopomofo_segs = segment_ascii(scramble)
    if not bopomofo_segs:
        await interaction.response.send_message(f"❌ 無法辨識亂碼 `{scramble}`")
        return

    bpmf_target = "".join(bopomofo_segs)
    success = engine.delete_word(word, bpmf_target)

    if success:
        embed = discord.Embed(
            title="🗑️ 已刪除詞彙",
            description=f"之後遇到 `{scramble}` 將不會翻譯成 {word}",
            color=discord.Color.green()
        )
        embed.add_field(name="已移除", value=f"{scramble} → {word}", inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"⚠️ 找不到 `{bpmf_target}` 與 **{word}** 的對應關係，刪除失敗。")

# --- 忽略指令：設定不需要翻譯的亂碼 (/ignore) ---
@bot.tree.command(name="ignore", description="設定不需要翻譯的亂碼模式（如人名）")
@app_commands.describe(pattern="亂碼模式 (例: alice, tom, john)")
async def ignore(interaction: discord.Interaction, pattern: str):
    if engine.add_ignore_pattern(pattern):
        embed = discord.Embed(
            title="🚫 已新增忽略模式",
            description=f"之後遇到 `{pattern}` 將不會翻譯",
            color=discord.Color.yellow()
        )
        embed.add_field(name="模式", value=pattern, inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"⚠️ 設定忽略模式失敗。")

# --- 取消忽略指令：取消不需要翻譯的亂碼 (/unignore) ---
@bot.tree.command(name="unignore", description="取消忽略模式")
@app_commands.describe(pattern="要取消忽略的亂碼模式")
async def unignore(interaction: discord.Interaction, pattern: str):
    if engine.remove_ignore_pattern(pattern):
        embed = discord.Embed(
            title="✅ 已取消忽略模式",
            description=f"模式 `{pattern}` 已移除",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"⚠️ 找不到忽略模式 `{pattern}`，取消失敗。")

# --- 查看忽略列表：列出所有忽略模式 (/ignores) ---
@bot.tree.command(name="ignores", description="列出所有不需要翻譯的亂碼模式")
async def ignores(interaction: discord.Interaction):
    patterns = engine.list_ignore_patterns()
    if not patterns:
        embed = discord.Embed(
            title="📋 忽略模式列表",
            description="目前沒有設定任何忽略模式",
            color=discord.Color.yellow()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="📋 忽略模式列表",
            color=discord.Color.yellow()
        )
        patterns_text = ""
        for pattern in patterns:
            patterns_text += f"• {pattern}\n"
        embed.add_field(name="模式", value=patterns_text, inline=False)
        embed.add_field(name="總計", value=f"共 {len(patterns)} 個模式", inline=False)
        await interaction.response.send_message(embed=embed)


# --- Modal 表單：用於修正翻譯 ---
class FixTranslationModal(Modal, title='修正翻譯'):
    def __init__(self, scramble, bopomofo_segs, original_message):
        super().__init__()
        self.scramble = scramble
        self.bopomofo_segs = bopomofo_segs
        self.original_message = original_message

    correct_word = TextInput(
        label='請輸入正確的中文翻譯',
        placeholder='例：家好',
        required=True,
        min_length=1
    )

    async def on_submit(self, interaction: discord.Interaction):
        word = self.correct_word.value
        _, bopomofo_segs = segment_ascii(self.scramble)

        if not bopomofo_segs or len(bopomofo_segs) != len(word):
            await interaction.response.send_message(
                f"❌ 字數不符！亂碼拆出 {len(bopomofo_segs)} 個音，但你給了 {len(word)} 個字。",
                ephemeral=True
            )
            return

        if engine.add_word(word, bopomofo_segs):
            # 更新原始訊息並移除按鈕
            new_embed = discord.Embed(
                title="🔍 翻譯結果",
                color=discord.Color.blue()
            )
            new_embed.add_field(name="誤輸入", value=self.scramble, inline=False)
            new_embed.add_field(name="實際意思", value=word, inline=False)
            new_embed.set_footer(text="✅ 已修正")

            await interaction.response.edit_message(embed=new_embed, view=None)
        else:
            await interaction.response.send_message("⚠️ 學習失敗。", ephemeral=True)


# --- View 按鈕：翻譯結果的反饋按鈕 ---
class TranslationView(View):
    def __init__(self, scramble, word, bopomofo_segs, original_author_id):
        super().__init__(timeout=None)
        self.scramble = scramble
        self.word = word
        self.bopomofo_segs = bopomofo_segs
        self.original_author_id = original_author_id

    @discord.ui.button(label='✅ 正確', style=discord.ButtonStyle.green)
    async def correct_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_author_id:
            await interaction.response.send_message("❌ 只有輸入亂碼的人可以修改", ephemeral=True)
            return

        full_bpmf = "".join([s.replace('ˉ', '').strip() for s in self.bopomofo_segs])
        if engine.increase_weight(self.word, full_bpmf):
            await interaction.response.edit_message(view=None)
            await interaction.followup.send("✅ 已記錄為正確翻譯", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ 操作失敗", ephemeral=True)

    @discord.ui.button(label='📝 修正翻譯', style=discord.ButtonStyle.primary)
    async def fix_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_author_id:
            await interaction.response.send_message("❌ 只有輸入亂碼的人可以修改", ephemeral=True)
            return

        modal = FixTranslationModal(self.scramble, self.bopomofo_segs, interaction.message)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🚫 忽略此亂碼', style=discord.ButtonStyle.red)
    async def ignore_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_author_id:
            await interaction.response.send_message("❌ 只有輸入亂碼的人可以修改", ephemeral=True)
            return

        if engine.add_ignore_pattern(self.scramble):
            # 更新 Embed 顯示已忽略
            new_embed = discord.Embed(
                title="🔍 翻譯結果",
                color=discord.Color.blue()
            )
            new_embed.add_field(name="誤輸入", value=self.scramble, inline=False)
            new_embed.add_field(name="實際意思", value=f"~~{self.word}~~ (已忽略)", inline=False)
            new_embed.set_footer(text="🚫 已加入忽略列表")

            await interaction.response.edit_message(embed=new_embed, view=None)
        else:
            await interaction.response.send_message("⚠️ 操作失敗", ephemeral=True)


bot.run(DISCORD_TOKEN)