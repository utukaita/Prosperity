from datamodel import OrderDepth, TradingState, Order
from typing import List
import jsonpickle
import statistics

LIMIT = 50  # maximum absolute position allowed
WINDOW_SIZE = 20  # number of most recent trades to consider for fair value calculation
GAP_MULTIPLIER = 20 # multiplier for gap size in order book

def ewma(prices, alpha=0.2):
    """
    Compute an exponential weighted moving average over the list of prices.
    alpha is the smoothing factor (0 < alpha <= 1).
    """
    if not prices:
        return 0
    avg = prices[0]
    for p in prices[1:]:
        avg = alpha * p + (1 - alpha) * avg
    return avg

def rolling_std(prices):
    """
    Compute standard deviation over the last N points.
    """
    if len(prices) < 2:
        return 1.0  # fallback
    return statistics.pstdev(prices)

def linear_regression(prices: List[float]):
    """
    A simple linear regression on price history.
    Uses x-values 0, 1, ..., n-1 and returns predicted price for x = n.
    """
    n = len(prices)
    if n == 0:
        return 0, 0
    if n == 1:
        return prices[0], 0
    xs = list(range(n))
    # Calculate slope and intercept
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(prices)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, prices))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den != 0 else 0
    intercept = mean_y - slope * mean_x
    # Predict price at x = n (next period)
    return (intercept + slope * n), slope


def compute_order_size(product: str, recent_prices: List[float], order_depth: OrderDepth, current_position: int,
                       fair_value: float) -> int:
    """
    Dynamically computes an order size.

    The size is influenced by:
      - A base scaling factor determined by product type.
      - Liquidity: estimated from the best bid/ask sizes.
      - Volatility: higher volatility (rolling std) yields smaller size.
      - The gap: if the current market price deviates significantly from the fair value,
        increase order size proportionally.

    The final computed size is clipped between 1 and 20.
    """
    if not recent_prices:
        return 1

    # Compute volatility
    vol = rolling_std(recent_prices)
    if vol == 0:
        vol = 1  # avoid division by zero

    # Set a base scale factor by product.
    if product == "RAINFOREST_RESIN":
        base_scale = 5
    elif product == "KELP":
        base_scale = 3
    elif product == "SQUID_INK":
        _, slope = linear_regression(recent_prices)
        base_scale = 6 if abs(slope) > 0.5 else 4
    else:
        base_scale = 5

    # Compute liquidity factor from order book.
    liquidity_factor = 0
    if order_depth.buy_orders and order_depth.sell_orders:
        best_bid_qty = max(order_depth.buy_orders.values())
        best_ask_qty = min(order_depth.sell_orders.values())
        liquidity_factor = (best_bid_qty + best_ask_qty) / 2.0
    elif order_depth.buy_orders:
        liquidity_factor = max(order_depth.buy_orders.values())
    elif order_depth.sell_orders:
        liquidity_factor = min(order_depth.sell_orders.values())
    else:
        liquidity_factor = base_scale  # default if order book is empty

    # Use the most recent market price as current price.
    current_price = recent_prices[-1]
    gap = abs(current_price - fair_value)
    gap_percentage = (gap / fair_value) * 100 if fair_value != 0 else 0
    gap_multiplier = 1 + (gap_percentage * GAP_MULTIPLIER)

    # Combine factors; computed size increases with liquidity and gap, decreases with volatility.
    computed_size = int(round(base_scale * (liquidity_factor / vol) * gap_multiplier))
    computed_size = max(3, computed_size)
    computed_size = min(computed_size, 20)  # cap order size at 20 units
    return computed_size

class Trader:
    def __init__(self):
        # Build a fresh rolling price map for fair value estimation.
        self.prices_map = {
            "RAINFOREST_RESIN": [],
            "KELP": [],
            "SQUID_INK": []
        }

    def run(self, state: TradingState):
        result = {}
        # Update rolling price data from market trades.
        for product in self.prices_map:
            if product in state.market_trades and len(state.market_trades[product]) > 0:
                # take the last trade price
                last_trade_price = state.market_trades[product][-1].price
                self.prices_map[product].append(last_trade_price)
                # keep only the most recent WINDOW_SIZE points
                self.prices_map[product] = self.prices_map[product][-WINDOW_SIZE:]

        fair_values = {}
        spread_map = {}
        for product, recent_prices in self.prices_map.items():
            if product == "RAINFOREST_RESIN":
                # stable
                fv = ewma(recent_prices, alpha=0.1)  # or just average
                vol = rolling_std(recent_prices)
                sprd = 2 * vol  # narrower
            elif product == "KELP":
                # unpredictable
                fv = ewma(recent_prices, alpha=0.3)  # more reactive
                vol = rolling_std(recent_prices)
                sprd = 3 * vol  # wide
            else:  # SQUID_INK
                # trending
                fv, slope = linear_regression(recent_prices)
                vol = rolling_std(recent_prices)
                sprd = 2 * vol  # moderate base spread
                sprd += 0.5 * abs(slope)
            fair_values[product] = fv
            # make sure spread is at least 1 to avoid zero
            spread_map[product] = max(1, sprd)

        # Now for each product that is in the order book, generate orders.
        # We generate two orders per product: one buy order and one sell order, with prices centered around fair value.
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            orders = []
            recent_prices = self.prices_map[product]
            if product in ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]:
                fv = fair_values[product]
                spread = spread_map[product]
                # Define bid price slightly below the fair value and ask price slightly above.
                bid_price = int(round(fv - spread / 2))
                ask_price = int(round(fv + spread / 2))

                # Get current position; default to 0 if not present.
                current_pos = state.position.get(product, 0)

                # Decide fixed order size for market making (adjustable).
                base_size = compute_order_size(product, recent_prices, order_depth, fv, current_pos)

                # Adjust order size if near limits.
                available_buy = LIMIT - current_pos  # buy orders are positive
                available_sell = LIMIT + current_pos  # sell orders are negative (we allow position down to -LIMIT)
                buy_size = min(base_size, available_buy) if available_buy > 0 else 0
                sell_size = min(base_size, available_sell) if available_sell > 0 else 0

                # Create a buy order at bid_price (buying is represented by a positive quantity).
                if buy_size > 0:
                    orders.append(Order(product, bid_price, buy_size))
                # Create a sell order at ask_price (selling is represented by a negative quantity).
                if sell_size > 0:
                    orders.append(Order(product, ask_price, -sell_size))

                # # Opportunistic orders: if the market's best ask is much lower than our bid, add extra buy.
                # if order_depth.sell_orders:
                #     best_market_ask = min(order_depth.sell_orders.keys(), key=int)
                #     if int(best_market_ask) < bid_price*0.9:
                #         extra_buy = min(order_depth.sell_orders[best_market_ask], available_buy - buy_size)
                #         if extra_buy > 0:
                #             orders.append(Order(product, int(best_market_ask), extra_buy))
                # if order_depth.buy_orders:
                #     best_market_bid = max(order_depth.buy_orders.keys(), key=int)
                #     if int(best_market_bid) > ask_price*0.9:
                #         extra_sell = min(order_depth.buy_orders[best_market_bid], available_sell - sell_size)
                #         if extra_sell > 0:
                #             orders.append(Order(product, int(best_market_bid), -extra_sell))

                result[product] = orders
            else:
                result[product] = []

                # --- Conversion Logic ---
                # Here we implement a simple conversion algorithm for SQUID_INK.
                # The conversion opportunity is evaluated using the conversion observation data.
        conversion_request = 0  # default: no conversion request
        conversion_limit = 5  # maximum units we can convert per round

        # Check if observations and conversionObservations are provided.
        if state.observations and hasattr(state.observations, "conversionObservations"):
            for product in ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]:
                if product in state.observations.conversionObservations:
                    conv_obs = state.observations.conversionObservations[product]
                    current_pos = state.position.get(product, 0)
                    # We only attempt conversion if we have a nonzero position.
                    if current_pos != 0:
                        # Calculate an effective conversion margin.
                        # (For example, if converting earns a spread between the conversion bid and ask, minus all fees.)
                        effective_margin = (conv_obs.bidPrice - conv_obs.askPrice) - (
                                    conv_obs.transportFees + conv_obs.exportTariff + conv_obs.importTariff)
                        # If the effective margin is positive, conversion might be profitable.
                        if effective_margin > 0:
                            # Request conversion for up to the lesser of the absolute position and the conversion limit.
                             conversion_request = min(abs(current_pos), conversion_limit)

        # For any products that do not appear in order_depths but we trade,
        # create default orders based on the calculated fair values.
        # for product in ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]:
        #     if product not in result:
        #         fv = fair_values[product]
        #         spread = spread_map[product]
        #         bid_price = int(round(fv - spread / 2))
        #         ask_price = int(round(fv + spread / 2))
        #         orders = []
        #         current_pos = state.position.get(product, 0)
        #         base_size = 5
        #         available_buy = LIMIT - current_pos
        #         available_sell = LIMIT + current_pos
        #         buy_size = min(base_size, available_buy) if available_buy > 0 else 0
        #         sell_size = min(base_size, available_sell) if available_sell > 0 else 0
        #         if buy_size > 0:
        #             orders.append(Order(product, bid_price, buy_size))
        #         if sell_size > 0:
        #             orders.append(Order(product, ask_price, -sell_size))
        #         result[product] = orders

        # Persist the updated historical prices so they continue across rounds.
        traderData = jsonpickle.encode(self.prices_map)
        return result, conversion_request, traderData
