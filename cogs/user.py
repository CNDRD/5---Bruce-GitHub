from func.firebase_init import db

import disnake
from disnake.ext.commands import Param
from disnake.ext import commands

from datetime import datetime
from pytz import timezone
import pytimeparse
import random
import yaml


# Config Load
local_timezone = yaml.safe_load(open("config.yml")).get("local_timezone")


class User(commands.Cog):
    def __init__(self, client):
        """Collection of short user facing commands."""
        self.client = client

    @commands.slash_command(name="timer", description="Set a timer for a certain amount of time.")
    async def _timer(
            self,
            inter: disnake.ApplicationCommandInteraction,
            time: str = Param(..., desc="Amount of time to set the timer for. Format: 1h 30m 15s"),
            message: str = Param('Timer will end', desc="Message that will be shown next to the timer. Defaults to 'Timer will end'"),
            relative: bool = Param(True, desc="Whether the timer should be relative to the current time or not."),
            public: bool = Param(True, desc="Whether or not to make the timer public. Defaults to True.")
    ):
        """Set a timer for a certain amount of time."""
        timestamp = int(pytimeparse.parse(time) + datetime.now().timestamp())
        await inter.response.send_message(f"{message} <t:{timestamp}:{'R' if relative else 'T'}>", ephemeral=not public)

    @commands.slash_command(name="claim", description="Claim your hourly shekel bonus")
    async def _claim(
            self,
            inter: disnake.ApplicationCommandInteraction
    ):
        today = datetime.now(timezone(local_timezone)).strftime("%Y-%m-%d-%H")
        usr = db.child("users").child(inter.author.id).get().val()
        last_claim = usr.get("last_money_claim", "0000-00-00-00")
        monies = usr.get("money")
        lvl = usr.get("level")
        claim_money = lvl * 1_000

        if last_claim != today:

            total_claimed = int(db.child("moneyTotals").child("claim").get().val() or 0)
            db.child("moneyTotals").child("claim").set(str(total_claimed + claim_money))

            db.child("users").child(inter.author.id).update({"money": monies + claim_money, "last_money_claim": today})
            return await inter.send(f"You have successfully claimed ₪**{claim_money:,}**!".replace(",", " "))

        midnight_ts = int(datetime.now(timezone(local_timezone)).replace(hour=0, minute=0, second=0).timestamp() + 86400)
        return await inter.send(content=f"You already claimed your shekels today! (Next claim available ~<t:{midnight_ts}:R>)")

    @commands.slash_command(name="send", description="Send shekels to someone")
    async def _send(
            self,
            inter: disnake.ApplicationCommandInteraction,
            user: disnake.Member = Param(..., desc="Who are you sending the shekels to?"),
            shekels: int = Param(..., desc="How much shekels are you sending?")
    ):
        if inter.author.id == user.id:
            return await inter.response.send_message(
                f"Successfully sent ₪**{shekels:,}** shekel{'s' if shekels > 1 else ''} to yourself, you dumb fuck..",
                ephemeral=True
            )
        
        if user.bot:
            return await inter.response.send_message("You can't send shekels to a bot..", ephemeral=True)
        
        author_money = db.child("users").child(inter.author.id).child("money").get().val() or 0
        
        if shekels > author_money:
            return await inter.response.send_message("Cannot send more shekels than you have..", ephemeral=True)
        
        user_money = db.child("users").child(user.id).child("money").get().val() or 0
        
        db.child("users").child(inter.author.id).update({"money": (author_money - shekels)})
        db.child("users").child(user.id).update({"money": (user_money + shekels)})
        
        await inter.response.send_message(
            f"Successfully sent ₪**{shekels:,}** shekel{'s' if shekels > 1 else ''} to {user.name}.\n"
            f"You now have ₪{(author_money - shekels):,}",
            ephemeral=True
        )
        
    @commands.slash_command(name="ping", description="Gets the bot's ping")
    async def ping(
            self,
            inter: disnake.ApplicationCommandInteraction
    ):
        await inter.response.send_message(f"Pong ({round(self.client.latency * 1000)}ms)")

    @commands.slash_command(name="code", description="Link to the source code on GitHub")
    async def code(
            self,
            inter: disnake.ApplicationCommandInteraction
    ):
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(label="GitHub", url="https://github.com/CNDRD/Bruce"))
        await inter.response.send_message(content="Here you go:", view=view)

    @commands.slash_command(name="coinflip", description="Flips a coin")
    async def coinflip(
            self,
            inter: disnake.ApplicationCommandInteraction,
            heads: str = Param("Heads", desc="What to send"),
            tails: str = Param("Tails", desc="What to send")
    ):
        outcomes = (heads, tails)
        msg = outcomes[random.SystemRandom().randint(0, 1)]
        await inter.response.send_message(f"**{msg}**", ephemeral=True)

    @commands.slash_command(name="money", description="Shows your balance")
    async def money(self, inter: disnake.ApplicationCommandInteraction):
        monies = db.child("users").child(inter.author.id).child("money").get().val()
        await inter.response.send_message(f"You have ₪{monies:,}", ephemeral=True)


def setup(client):
    client.add_cog(User(client))
