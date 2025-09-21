from datamodel import OrderDepth, TradingState, Order
from typing import List
import jsonpickle

# Global position limit for each asset.
LIMIT = 50


class Trader:
    def __init__(self):
        # Use an instance variable for the historical prices.
        # It will be restored from traderData, or defaulted on the first run.
        self.historical_prices = None

    def run(self, state: TradingState):
        result = {}

        # Restore previous historical data if available, otherwise initialize defaults.
        if state.traderData:
            try:
                self.historical_prices = jsonpickle.decode(state.traderData)
            except Exception as e:
                print("Error decoding traderData, reinitializing historical_prices:", e)
                self.historical_prices = None

        if not self.historical_prices:
            # Initialize default historical prices (as if read from CSVs)
            # These arrays are ordered from oldest to newest.
            self.historical_prices = {
                "RAINFOREST_RESIN": [100, 100, 101],  # stable prices
                "KELP": [50, 70, 55],  # unpredictable prices
                "SQUID_INK": [40, 42, 44]  # trending upward
            }

        # For SQUID_INK, compute a simple trend: (newest - oldest) divided by (n-1)
        squid_prices = self.historical_prices.get("SQUID_INK", [])
        if len(squid_prices) >= 2:
            squid_trend = (squid_prices[-1] - squid_prices[0]) / (len(squid_prices) - 1)
        else:
            squid_trend = 0

        # Process each product for which we have order book data.
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Focus on our three assets.
            if product in ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]:
                # Compute the baseline fair value from historical prices.
                prices_hist = self.historical_prices.get(product, [])
                if prices_hist:
                    avg_price = sum(prices_hist) / len(prices_hist)
                else:
                    # Default fallback value if no history exists.
                    avg_price = 10 if product == "RAINFOREST_RESIN" else 20

                fair_value = avg_price

                if product == "SQUID_INK":
                    # Adjust fair value based on the upward trend for squid ink.
                    # Here we use half of the computed trend as a simple adjustment.
                    fair_value = avg_price + 0.5 * squid_trend

                # For kelp, because it is unpredictable, we trade more cautiously.
                # For example, we might decide to trade only if the mispricing is significant.
                # (For now, we keep the same fair value but one might add a wider margin.)

                # Get the current position for the product (default to 0).
                current_position = state.position.get(product, 0)

                # --- BUY LOGIC: Look to buy if the best ask price is below fair value.
                if order_depth.sell_orders:
                    best_ask = min(order_depth.sell_orders.keys(), key=int)
                    available_qty = order_depth.sell_orders[best_ask]
                    if int(best_ask) < fair_value:
                        # Determine how many units we can buy. In our simulation,
                        # buying is indicated by negative order quantities, and
                        # we cannot exceed a position of -LIMIT.
                        max_buy = abs((-LIMIT) - current_position)
                        qty = min(available_qty, max_buy)
                        if qty > 0:
                            orders.append(Order(product, int(best_ask), -qty))

                # --- SELL LOGIC: Look to sell if the best bid price is above fair value.
                if order_depth.buy_orders:
                    best_bid = max(order_depth.buy_orders.keys(), key=int)
                    available_qty = order_depth.buy_orders[best_bid]
                    if int(best_bid) > fair_value:
                        # Determine how many units we can sell without exceeding +LIMIT.
                        max_sell = LIMIT - current_position
                        qty = min(available_qty, max_sell)
                        if qty > 0:
                            orders.append(Order(product, int(best_bid), qty))

                result[product] = orders
            else:
                # For assets we do not trade, leave orders empty.
                result[product] = []

        # Here we could update our historical data further if new reliable market information is available.
        # For this preliminary version, the historical prices remain unchanged.

        # Save our internal state in traderData so it persists between rounds.
        traderData = jsonpickle.encode(self.historical_prices)
        conversions = 1
        return result, conversions, traderData
