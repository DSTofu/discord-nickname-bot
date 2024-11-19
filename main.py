import discord
from discord.ext import commands, tasks
import random
from itertools import cycle
from datetime import datetime, timedelta
import asyncio  # For timeout handling
import os
from keep_alive import keep_alive

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$nick', intents=intents)

user_nicknames = {}
user_schedules = {}
GUILD_ID = 472449051753840651  # Replace with your actual guild ID

# Helper functions
def calculate_next_time_local(interval_type, interval_value):
    """Calculate next change time based on interval type and value."""
    now = datetime.now()
    if interval_type == 'minutes':
        return now + timedelta(minutes=interval_value)
    elif interval_type == 'hours':
        return now + timedelta(hours=interval_value)
    elif interval_type == 'days':
        return now + timedelta(days=interval_value)
    return now

def calculate_next_midnight():
    """Calculate the next occurrence of 12:00 AM local time."""
    now = datetime.now()
    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return next_midnight

# Task to change nicknames
@tasks.loop(minutes=1)  # Check every minute
async def change_nicknames():
    now = datetime.now()
    for user_id, schedule in user_schedules.items():
        if schedule["next_change"] <= now:
            guild = bot.get_guild(GUILD_ID)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    data = user_nicknames[user_id]
                    new_nickname = (
                        random.choice(data["names"])
                        if data["mode"] == "random"
                        else next(data["cycle"])
                    )
                    try:
                        await member.edit(nick=new_nickname)
                        print(f"Changed {member.name}'s nickname to: {new_nickname}")
                    except discord.Forbidden:
                        print(f"No permission to change {member.name}'s nickname")

            # Update next change time
            if schedule["interval_type"] == 'daily':
                schedule["next_change"] = calculate_next_midnight()
            else:
                schedule["next_change"] = calculate_next_time_local(
                    schedule["interval_type"], schedule["interval_value"]
                )

@change_nicknames.before_loop
async def before_change_nicknames():
    await bot.wait_until_ready()

# Event handler for bot startup
@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')
    if not change_nicknames.is_running():
        change_nicknames.start()

# Command to update nicknames
@bot.command(name='updatenames')
async def update_names(ctx):
    await ctx.send("Please send your nicknames separated by commas (e.g., Nick1, Nick2, Nick3).")

    def check(m):
        return m.author.id == ctx.author.id and m.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', timeout=300.0, check=check)
        new_nicknames = [name.strip() for name in msg.content.split(',') if name.strip()]

        if not new_nicknames:
            await ctx.send("No valid nicknames provided. Please try again.")
            return

        await ctx.send(
            "How would you like your nicknames to cycle?\n"
            "Type 'random' for random selection or 'order' for sequential order."
        )
        mode_msg = await bot.wait_for('message', timeout=30.0, check=check)
        mode = mode_msg.content.lower()

        if mode not in ['random', 'order']:
            await ctx.send("Invalid mode. Defaulting to random mode.")
            mode = 'random'

        await ctx.send(
            "Set the interval type (minutes, hours, days, or daily):"
        )
        interval_type_msg = await bot.wait_for('message', timeout=30.0, check=check)
        interval_type = interval_type_msg.content.lower()

        if interval_type not in ['minutes', 'hours', 'days', 'daily']:
            await ctx.send("Invalid interval type. Defaulting to daily.")
            interval_type = 'daily'

        interval_value = 1
        if interval_type != 'daily':
            await ctx.send("Set the interval value (e.g., 30 for 30 minutes):")
            interval_value_msg = await bot.wait_for('message', timeout=30.0, check=check)

            if not interval_value_msg.content.isdigit():
                await ctx.send("Invalid interval value. Defaulting to 1.")
            else:
                interval_value = int(interval_value_msg.content)

        next_change = (
            calculate_next_midnight()
            if interval_type == 'daily'
            else calculate_next_time_local(interval_type, interval_value)
        )

        user_nicknames[ctx.author.id] = {
            "names": new_nicknames,
            "mode": mode,
            "cycle": cycle(new_nicknames) if mode == 'order' else None,
        }
        user_schedules[ctx.author.id] = {
            "interval_type": interval_type,
            "interval_value": interval_value,
            "next_change": next_change,
        }

        await ctx.send(
            f"Updated your nickname list with {len(new_nicknames)} names in {mode} mode:\n" +
            "\n".join(f"{i+1}. {name}" for i, name in enumerate(new_nicknames))
        )

    except asyncio.TimeoutError:
        await ctx.send("Timeout reached. Update cancelled.")

# Command to show nicknames
@bot.command(name='shownames')
async def show_names(ctx):
    if ctx.author.id in user_nicknames and user_nicknames[ctx.author.id]["names"]:
        data = user_nicknames[ctx.author.id]
        mode_text = "random selection" if data["mode"] == "random" else "sequential order"
        await ctx.send(
            f"Your current nickname list ({mode_text} mode):\n" +
            "\n".join(f"{i+1}. {name}" for i, name in enumerate(data["names"]))
        )
    else:
        await ctx.send("You don't have any nicknames set up yet. Use $nickupdatenames to add some!")

# Command to add nicknames
@bot.command(name='addnames')
async def add_names(ctx):
    if ctx.author.id not in user_nicknames or not user_nicknames[ctx.author.id]["names"]:
        await ctx.send("You don't have any nicknames set up yet. Use $nickupdatenames to add some!")
        return

    await ctx.send("Please send the nicknames you'd like to add, separated by commas (e.g., Nick4, Nick5).")

    def check(m):
        return m.author.id == ctx.author.id and m.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', timeout=300.0, check=check)
        new_nicknames = [name.strip() for name in msg.content.split(',') if name.strip()]

        if not new_nicknames:
            await ctx.send("No valid nicknames provided. Please try again.")
            return

        user_nicknames[ctx.author.id]["names"].extend(new_nicknames)

        if user_nicknames[ctx.author.id]["mode"] == "order":
            user_nicknames[ctx.author.id]["cycle"] = cycle(user_nicknames[ctx.author.id]["names"])

        await ctx.send(
            f"Added {len(new_nicknames)} nicknames to your list.\n" +
            "\n".join(f"{i+1}. {name}" for i, name in enumerate(user_nicknames[ctx.author.id]["names"]))
        )

    except asyncio.TimeoutError:
        await ctx.send("Timeout reached. Adding nicknames cancelled.")

# Command to delete nicknames
@bot.command(name='deletenames')
async def delete_names(ctx):
    if ctx.author.id not in user_nicknames or not user_nicknames[ctx.author.id]["names"]:
        await ctx.send("You don't have any nicknames set up yet. Use $nickupdatenames to add some!")
        return

    await ctx.send("Send the nicknames or indices to delete, separated by commas (e.g., Nick2, 3).")

    def check(m):
        return m.author.id == ctx.author.id and m.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', timeout=300.0, check=check)
        items_to_delete = msg.content.split(',')

        nicknames = user_nicknames[ctx.author.id]["names"]
        updated_list = nicknames[:]
        removed_names = []

        for item in items_to_delete:
            item = item.strip()
            if item.isdigit():
                index = int(item) - 1
                if 0 <= index < len(nicknames):
                    removed_names.append(nicknames[index])
                    updated_list.remove(nicknames[index])
            elif item in nicknames:
                removed_names.append(item)
                updated_list.remove(item)

        if not removed_names:
            await ctx.send("No valid nicknames or indices provided. Please try again.")
            return

        user_nicknames[ctx.author.id]["names"] = updated_list

        if user_nicknames[ctx.author.id]["mode"] == "order":
            user_nicknames[ctx.author.id]["cycle"] = cycle(updated_list)

        await ctx.send(
            f"Deleted {len(removed_names)} nicknames:\n" +
            "\n".join(f"- {name}" for name in removed_names) +
            "\n\nUpdated list:\n" +
            "\n".join(f"{i+1}. {name}" for i, name in enumerate(updated_list))
        )

    except asyncio.TimeoutError:
        await ctx.send("Timeout reached. Deleting nicknames cancelled.")

# Command for help
@bot.command(name='tulong')
async def help_command(ctx):
    help_text = """
**Available Commands:**
- `$nickupdatenames` - Start updating your nickname list with a specified interval and mode.
- `$nickaddnames` - Add new nicknames to the end of your existing list.
- `$nickdeletenames` - Delete specific nicknames by name or index from your list.
- `$nickshownames` - Show your current nickname list, mode, and interval settings.
- `$nickchangemode` - Switch between random and sequential cycling modes for your nicknames.
- `$nicktulong` - Show this help message.

**Interval Options:**
- **Minutes**: Set nicknames to change every X minutes.
- **Hours**: Set nicknames to change every X hours.
- **Days**: Set nicknames to change every X days.
- **Daily**: Nicknames change automatically at the start of the next day (12:00 AM local time).

**How to use:**
1. Type `$nickupdatenames`.
2. Send your nicknames separated by commas (e.g., Nick1, Nick2, Nick3).
3. Choose your cycling mode: 'random' or 'order'.
4. Set an interval type (minutes, hours, days, daily).
5. (If applicable) Set an interval value for minutes, hours, or days.

**Additional Commands:**
- Add nicknames with `$nickaddnames`.
- Remove specific nicknames with `$nickdeletenames`.

**Modes:**
- **Random**: Picks a random nickname at each interval.
- **Order**: Cycles through your list sequentially, then loops.
    """
    await ctx.send(help_text)

# Run bot
TOKEN = os.getenv("TOKEN")
keep_alive()
bot.run(TOKEN)
