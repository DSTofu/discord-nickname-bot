import discord
from discord.ext import commands, tasks
import random
from itertools import cycle
import os
from keep_alive import keep_alive
import asyncio  # Added for TimeoutError

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$nick', intents=intents)

user_nicknames = {}
GUILD_ID = 472449051753840651  # Replace with your actual guild ID

# Task to change nicknames daily
@tasks.loop(hours=24)
async def change_nicknames():
    guild = bot.get_guild(GUILD_ID)
    if guild:
        for user_id, data in user_nicknames.items():
            if data["names"]:
                member = guild.get_member(user_id)
                if member:
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

        user_nicknames[ctx.author.id] = {
            "names": new_nicknames,
            "mode": mode,
            "cycle": cycle(new_nicknames) if mode == 'order' else None,
        }

        mode_text = "random selection" if mode == "random" else "sequential order"
        await ctx.send(
            f"Updated your nickname list with {len(new_nicknames)} names in {mode_text} mode:\n" +
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

# Command to change mode
@bot.command(name='changemode')
async def change_mode(ctx):
    if ctx.author.id not in user_nicknames or not user_nicknames[ctx.author.id]["names"]:
        await ctx.send("You need to set up nicknames first using $nickupdatenames.")
        return

    data = user_nicknames[ctx.author.id]
    current_mode = data["mode"]
    new_mode = "order" if current_mode == "random" else "random"

    user_nicknames[ctx.author.id]["mode"] = new_mode
    if new_mode == "order":
        user_nicknames[ctx.author.id]["cycle"] = cycle(data["names"])
    else:
        user_nicknames[ctx.author.id]["cycle"] = None

    await ctx.send(f"Changed your nickname cycle mode from {current_mode} to {new_mode}.")

# Command to remove nicknames
@bot.command(name='removenames')
async def remove_names(ctx):
    if ctx.author.id in user_nicknames:
        del user_nicknames[ctx.author.id]
        await ctx.send("Your nickname list has been removed. Your nickname will no longer auto-change.")
    else:
        await ctx.send("You didn't have any nicknames set up.")

# Command for help
@bot.command(name='tulong')
async def help_command(ctx):
    help_text = """
**Available Commands:**
- `$nickupdatenames` - Start updating your nickname list
- `$nickshownames` - Show your current nickname list
- `$nickchangemode` - Switch between random and ordered mode
- `$nickremovenames` - Remove your nickname list and stop auto-changing
- `$nicktulong` - Show this help message

**Modes:**
- Random: Picks a random nickname each day
- Order: Goes through your list in sequence, then loops.

**How to use:**
1. Type `$nickupdatenames`
2. Send your nicknames separated by commas (e.g., Nick1, Nick2, Nick3).
3. Choose mode (random/order).
    """
    await ctx.send(help_text)

# Keep bot alive and start
keep_alive()
TOKEN = os.environ['TOKEN']
bot.run(TOKEN)
