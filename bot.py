import json
import discord
from discord.ext import commands
from discord.ui import View, Button
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_ROLE_ID = 1445776669947330735
FLOW_CATEGORY_ID = 1445776278044147753
ARCHIVE_CATEGORY_ID = 1445776278044147752
SUCCESS_ROLE_ID = 1445777114962858146
COPY_MESSAGE_URL = "https://canary.discord.com/channels/1445776277427458165/1445777468135837778/1445777536675221607"

# 質問データをロード
with open("embed.json", encoding="utf-8") as f:
    QUESTIONS = json.load(f)


# --- 参加時処理 ------------------------------------------------------
@bot.event
async def on_member_join(member: discord.Member):

    if member.bot:
        return

    is_default = member.display_avatar == member.default_avatar
    if is_default:
        try:
            await member.send("初期アイコンからの変更をお願いします。")
        except:
            pass
        return

    await start_flow(member)


# --- アイコン変更検知 ------------------------------------------------
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.display_avatar == before.default_avatar and \
       after.display_avatar != after.default_avatar:
        await start_flow(after)


# --- 説明フロー開始処理 --------------------------------------------
async def start_flow(member: discord.Member):

    guild = member.guild
    admin_role = guild.get_role(ADMIN_ROLE_ID)

    # 個人用チャンネル作成
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True)
    }

    category = guild.get_channel(FLOW_CATEGORY_ID)
    channel = await guild.create_text_channel(
        name=f"flow-{member.id}",
        overwrites=overwrites,
        category=category
    )

    await send_question(channel, member, 0)


# --- 質問出題 ---------------------------------------------------------
async def send_question(channel, member, index):

    if index >= len(QUESTIONS):
        await complete_flow(channel, member)
        return

    q = QUESTIONS[index]
    embed = discord.Embed(description=q["text"])

    view = FlowView(member_id=member.id, index=index)
    for i, choice in enumerate(q["choices"]):
        view.add_item(FlowButton(label=choice, idx=i))

    await channel.send(embed=embed, view=view)


# --- View / Button ---------------------------------------------------
class FlowView(View):
    def __init__(self, member_id, index):
        super().__init__(timeout=None)
        self.member_id = member_id
        self.index = index

    async def interaction_check(self, interaction):
        return interaction.user.id == self.member_id


class FlowButton(Button):
    def __init__(self, label, idx):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.idx = idx

    async def callback(self, interaction):
        q = QUESTIONS[self.view.index]

        if self.idx == q["answer"]:
            # 正解 → 次へ
            await interaction.response.send_message("ありがとうございます。")
            await send_question(interaction.channel, interaction.user, self.view.index + 1)
        else:
          # 不正解時の処理
          try:
              await interaction.user.send("参加資格がないようです。")
          except:
              pass  # DMをブロックしている場合など

          await interaction.guild.kick(
              interaction.user,
              reason="説明フロー不正解"
          )

          await interaction.response.send_message(
              f"{interaction.user.mention} を不正解のため退出処理しました。",
              ephemeral=False
          )



# --- 説明フロー完了 --------------------------------------------------
async def complete_flow(channel, member):

    # ロール付与
    role = member.guild.get_role(SUCCESS_ROLE_ID)
    await member.add_roles(role)

    # チャンネルをアーカイブカテゴリへ移動
    archive = member.guild.get_channel(ARCHIVE_CATEGORY_ID)
    await channel.edit(category=archive)

    # 本人から見えなくする
    await channel.set_permissions(member, read_messages=False)

    # DM送信（メッセージ内容コピー）
    content = await fetch_message_text(COPY_MESSAGE_URL, member.guild)
    try:
        await member.send(content)
    except:
        pass


async def fetch_message_text(url: str, guild: discord.Guild):
    parts = url.split("/")
    channel_id = int(parts[-2])
    message_id = int(parts[-1])

    channel = guild.get_channel(channel_id)
    msg = await channel.fetch_message(message_id)

    return msg.content

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

