from func.firebase_init import db
from func.stuff import add_spaces
from func.trading import get_current_price, get_multiple_prices, get_trading_buy_db

from disnake.ext.commands import Param
from disnake.ext import commands
import disnake

from typing import Literal


class Trading(commands.Cog):
    def __init__(self, client):
        """Trading simulator with real stocks."""
        self.client = client

    @commands.slash_command(name="trade", description="Trading bruh")
    async def _trade(
            self,
            inter: disnake.MessageInteraction,
            operation: Literal["Buy", "Sell", "View"] = Param(..., desc="Are you buying, selling or just wanna view your portfolio?"),
            stock: str = Param(None, desc="Symbol for the stock you wish to trade (Required when buying or selling)"),
            amount: int = Param(None, desc="How many stocks do you wish to buy/sell (Required only when buying)")
    ):
        await inter.response.defer()

        if stock is not None:
            stock = stock.upper()
            stock = stock.replace('/', '-')

        user_money = db.child("users").child(inter.author.id).child("money").get().val()
        currently_owns = db.child("trading").child(inter.author.id).get().val() or None

        match operation:
            case 'Buy':
                if stock is None or amount is None:
                    return await inter.edit_original_message(content=f"**All** parameters are **required** when buying!")
                if currently_owns is not None and stock in currently_owns:
                    return await inter.edit_original_message(content=f"You already own shares of **{stock}**")

                current_price = get_current_price(stock)
                buying_cost = current_price * amount
                if buying_cost > user_money:
                    return await inter.edit_original_message(content=f"You don't have enough money for this ({add_spaces(int(buying_cost))} > {add_spaces(user_money)})")

                db.child("trading").child(inter.author.id).update(get_trading_buy_db(stock, amount, current_price))
                db.child("users").child(inter.author.id).update({"money": int(user_money - buying_cost)})
                return await inter.edit_original_message(content=f"Successfully bought *{add_spaces(amount)}* shares of **{stock.replace('-', '/')}** for *{add_spaces(int(buying_cost))}* shekels")

            case 'Sell':
                if currently_owns is None:
                    return await inter.edit_original_message(content="You don't own any stocks!")
                if stock is None:
                    return await inter.edit_original_message(content="You have to specify which stock to sell!")
                if stock not in currently_owns:
                    return await inter.edit_original_message(content="You cannot sell a stock that you don't own!")

                bought_at = currently_owns.get(stock).get("boughtAt")
                amount_bought = currently_owns.get(stock).get("amount")
                bought_cost = bought_at * amount_bought

                current_price = get_current_price(stock)
                selling_cost = current_price * amount_bought

                profit_loss = "loss"
                outcome_money = bought_cost - selling_cost

                if selling_cost >= bought_cost:
                    profit_loss = "profit"
                    outcome_money = selling_cost - bought_cost

                db.child("trading").child(inter.author.id).child(stock).remove()
                db.child("users").child(inter.author.id).update({"money": int(user_money + selling_cost)})

                msg = f"Successfully sold *{amount_bought}* stocks of **{stock.replace('-', '/')}** for a {profit_loss} of `{add_spaces(int(outcome_money))}` shekels"
                return await inter.edit_original_message(content=msg)

            case "View":
                if currently_owns is None:
                    return await inter.edit_original_message(content="You don't own any stocks!")

                msg = "__Your current stonks sir:__\n\n"
                currently_owns_prices = get_multiple_prices(currently_owns)

                for stonk in currently_owns:
                    current_price = currently_owns_prices[stonk.replace('-', '/')]
                    bought_price = currently_owns[stonk]['boughtAt']
                    amount_bought = currently_owns[stonk]['amount']
                    profit = (current_price*amount_bought)-(bought_price*amount_bought)

                    msg += f"**{stonk.replace('-', '/')}** - " \
                           f"Current Price: `{current_price}` | " \
                           f"Bought at: `{bought_price}` | " \
                           f"Profit: `{add_spaces(int(profit))}` " \
                           f"*({amount_bought} stock{'s' if amount_bought > 1 else ''})*\n"

                return await inter.edit_original_message(content=msg)


def setup(client):
    client.add_cog(Trading(client))
