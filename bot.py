import discord
from discord.ext import commands, tasks
import json
import os

TOKEN = os.getenv("TOKEN")
PREFIX = "?"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

DATA_FILE = "points.json"

# =========================
# LƯU / ĐỌC ĐIỂM
# =========================

def load_points():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


points = load_points()


def save_points():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(points, f, ensure_ascii=False, indent=4)


def get_roles(member):
    """
    Lấy toàn bộ role của member, bỏ @everyone.
    Sắp xếp theo ID để so sánh chính xác.
    """
    return tuple(sorted(
        role.id
        for role in member.roles
        if role != member.guild.default_role
    ))


def same_roles(member1, member2):
    return get_roles(member1) == get_roles(member2)


def add_point(member, amount=1):
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    if guild_id not in points:
        points[guild_id] = {}

    if user_id not in points[guild_id]:
        points[guild_id][user_id] = 0

    points[guild_id][user_id] += amount
    save_points()


# =========================
# CỘNG ĐIỂM KHI CÙNG ROOM
# =========================

@tasks.loop(minutes=1)
async def room_points():

    for guild in bot.guilds:

        # Các thành viên đang ở voice
        members = [
            m for m in guild.members
            if m.voice
            and m.voice.channel
            and not m.bot
        ]

        # Chia theo từng room
        rooms = {}

        for member in members:
            channel_id = member.voice.channel.id

            if channel_id not in rooms:
                rooms[channel_id] = []

            rooms[channel_id].append(member)

        # Kiểm tra từng room
        for room_members in rooms.values():

            if len(room_members) < 2:
                continue

            # Mỗi cặp người trong room
            for i in range(len(room_members)):
                for j in range(i + 1, len(room_members)):

                    member1 = room_members[i]
                    member2 = room_members[j]

                    # ROLE PHẢI GIỐNG HỆT NHAU
                    if same_roles(member1, member2):

                        # Mỗi người +1
                        add_point(member1)
                        add_point(member2)


# =========================
# TAG NHAU
# =========================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Có người được tag
    if message.mentions:

        author = message.author

        for target in message.mentions:

            if target.bot:
                continue

            # Cùng server
            if target.guild.id != message.guild.id:
                continue

            # ROLE PHẢI GIỐNG HỆT NHAU
            if same_roles(author, target):

                # Người tag được +1
                add_point(author)

    await bot.process_commands(message)


# =========================
# LỆNH XEM ĐIỂM
# =========================

@bot.command()
async def diem(ctx, member: discord.Member = None):

    if member is None:
        member = ctx.author

    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    score = points.get(guild_id, {}).get(user_id, 0)

    await ctx.send(
        f"🏆 **{member.display_name}** hiện có **{score} điểm**."
    )


# =========================
# TOP ĐIỂM
# =========================

@bot.command()
async def top(ctx):

    guild_id = str(ctx.guild.id)

    data = points.get(guild_id, {})

    if not data:
        await ctx.send("Chưa có ai có điểm.")
        return

    ranking = sorted(
        data.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    text = "🏆 **TOP ĐIỂM**\n\n"

    for index, (user_id, score) in enumerate(ranking, 1):

        member = ctx.guild.get_member(int(user_id))

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

        text += f"**{index}.** {name} — `{score}` điểm\n"

    await ctx.send(text)


# =========================
# BOT ONLINE
# =========================

@bot.event
async def on_ready():

    print(f"✅ Bot online: {bot.user}")

    if not room_points.is_running():
        room_points.start()


bot.run(TOKEN)
