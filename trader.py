from datamodel import OrderDepth, TradingState, Order
from typing import List
import jsonpickle
import pandas as pd

LIMIT = 50  # position limit: each product must remain between -50 and 50


class Trader:
    def __init__(self):
        # Load historical price data from provided CSV files.
        # We assume the files are in order from oldest to newest.
        self.historical_prices = {
            "RAINFOREST_RESIN": [],
            "KELP": [],
            "SQUID_INK": []
        }
        # List CSV file names – adjust if the filenames change.
        file_names = [
            "prices_round_1_day_-2.csv",
            "prices_round_1_day_-1.csv",
            "prices_round_1_day_0.csv"
        ]
        for fname in file_names:
            try:
                df = pd.read_csv(fname)
                # Assume each CSV has at least columns: "product" and "price"
                for product in self.historical_prices.keys():
                    # If the product exists in this file, take its (first) price.
                    if product in df["product"].values:
                        price = df[df["product"] == product]["price"].iloc[0]
                        self.historical_prices[product].append(price)
            except Exception as e:
                print(f"Error loading file {fname}: {e}")

        # For SQUID_INK, precompute a simple trend adjustment
        # (using oldest and most recent prices if available)
        if len(self.historical_prices["SQUID_INK"]) >= 2:
            oldest = self.historical_prices["SQUID_INK"][0]
            newest = self.historical_prices["SQUID_INK"][-1]
            # A simple measure of trend (price change per day)
            self.squid_ink_trend = (newest - oldest) / (len(self.historical_prices["SQUID_INK"]) - 1)
        else:
            self.squid_ink_trend = 0

    def run(self, state: TradingState):
        result = {}
        # Process each product for which we have order depth data.
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            # Only trade on our three focus products.
            if product in ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]:
                # Compute a baseline "fair value" from historical data.
                prices_hist = self.historical_prices.get(product, [])
                if prices_hist:
                    avg_price = sum(prices_hist) / len(prices_hist)
                else:
                    # Fallback defaults if no history available.
                    avg_price = 10 if product == "RAINFOREST_RESIN" else 20
                fair_value = avg_price

                if product == "SQUID_INK":
                    # For squid ink, adjust fair value according to observed trend.
                    # (Here we use half the trend per day as an adjustment factor.)
                    fair_value = avg_price + 0.5 * self.squid_ink_trend

                # Get current position (if not present, assume zero).
                current_position = state.position.get(product, 0)

                # --- BUY LOGIC: look to purchase if the market's asking price is below fair value.
                if order_depth.sell_orders:
                    # Best ask: lowest selling price.
                    best_ask = min(order_depth.sell_orders.keys(), key=int)
                    available_qty = order_depth.sell_orders[best_ask]
                    # If the ask price is attractive, then buy.
                    if int(best_ask) < fair_value:
                        # Determine maximum additional units we can buy without exceeding -LIMIT.
                        # (In this simulation convention, buying is indicated by a negative order quantity.)
                        max_buy = abs((-LIMIT) - current_position)
                        # Trade at most the available quantity or our remaining room.
                        qty = min(available_qty, max_buy)
                        if qty > 0:
                            orders.append(Order(product, int(best_ask), -qty))

                # --- SELL LOGIC: look to sell if the market's bid price exceeds fair value.
                if order_depth.buy_orders:
                    # Best bid: highest buying price.
                    best_bid = max(order_depth.buy_orders.keys(), key=int)
                    available_qty = order_depth.buy_orders[best_bid]
                    if int(best_bid) > fair_value:
                        # Determine how many units we can sell without exceeding +LIMIT.
                        max_sell = LIMIT - current_position
                        qty = min(available_qty, max_sell)
                        if qty > 0:
                            orders.append(Order(product, int(best_bid), qty))

                # Assign orders for this product.
                result[product] = orders
            else:
                result[product] = []

        # Save state data (here we simply encode our historical prices so far).
        traderData = jsonpickle.encode(self.historical_prices)
        conversions = 1
        return result, conversions, traderData
