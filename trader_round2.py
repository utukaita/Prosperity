from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import jsonpickle
import statistics

# ------------------------------
# Position Limits (Round 2)
# ------------------------------
POSITION_LIMITS = {
    "CROISSANTS": 250,
    "JAMS": 350,
    "DJEMBES": 60,
    "PICNIC_BASKET1": 60,
    "PICNIC_BASKET2": 100,
}

# ------------------------------
# Parameters for Order Sizing & Spread
# ------------------------------
GAP_MULTIPLIER = 20  # multiplier applied to gap percentage
WINDOW_SIZE = 20  # recent trade window


# ------------------------------
# Helper Statistical Functions
# ------------------------------
def ewma(prices: List[float], alpha: float = 0.2) -> float:
    """Compute an Exponential Weighted Moving Average over a price list."""
    if not prices:
        return 0.0
    avg = prices[0]
    for p in prices[1:]:
        avg = alpha * p + (1 - alpha) * avg
    return avg


def rolling_std(prices: List[float]) -> float:
    """Compute the rolling standard deviation. Fallback to 1.0 if insufficient data."""
    if len(prices) < 2:
        return 1.0
    return statistics.pstdev(prices)


def linear_regression(prices: List[float]) -> (float, float):
    """
    Perform a simple linear regression on price history.
    Returns the predicted next price and the slope.
    """
    n = len(prices)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        return prices[0], 0.0
    xs = list(range(n))
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(prices)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, prices))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den != 0 else 0.0
    intercept = mean_y - slope * mean_x
    return (intercept + slope * n), slope


def compute_order_size(product: str, recent_prices: List[float],
                       order_depth: OrderDepth, current_position: int,
                       fair_value: float) -> int:
    """
    Dynamically compute an order size based on liquidity, volatility, and gap.

    Order size is affected by:
      - Base scale (which may be different for baskets vs. ingredients)
      - Liquidity from the order book
      - Volatility (via rolling standard deviation)
      - The price gap relative to fair value (amplified by GAP_MULTIPLIER)

    The size is bounded between 3 and 20 units.
    """
    if not recent_prices:
        return 1

    vol = rolling_std(recent_prices)
    if vol == 0:
        vol = 1.0

    if product in ["CROISSANTS", "JAMS"]:
        base_scale = 5
    elif product == "DJEMBES":
        _, slope = linear_regression(recent_prices)
        base_scale = 6 if abs(slope) > 0.5 else 4
    elif product in ["PICNIC_BASKET1", "PICNIC_BASKET2"]:
        base_scale = 3  # assume baskets are less liquid
    else:
        base_scale = 5

    liquidity_factor = 0.0
    if order_depth.buy_orders and order_depth.sell_orders:
        best_bid_qty = max(order_depth.buy_orders.values())
        best_ask_qty = min(order_depth.sell_orders.values())
        liquidity_factor = (best_bid_qty + best_ask_qty) / 2.0
    elif order_depth.buy_orders:
        liquidity_factor = max(order_depth.buy_orders.values())
    elif order_depth.sell_orders:
        liquidity_factor = min(order_depth.sell_orders.values())
    else:
        liquidity_factor = base_scale

    current_price = recent_prices[-1]
    gap = abs(current_price - fair_value)
    gap_percentage = (gap / fair_value * 100) if fair_value != 0 else 0
    gap_multiplier = 1 + (gap_percentage * GAP_MULTIPLIER)
    computed_size = int(round(base_scale * (liquidity_factor / vol) * gap_multiplier))
    computed_size = max(3, computed_size)
    computed_size = min(computed_size, 20)
    return computed_size


# ------------------------------
# Trader Class for Round 2
# ------------------------------
class Trader:
    def __init__(self):
        # Maintain rolling price data for the individual ingredients.
        self.prices_map = {
            "CROISSANTS": [],
            "JAMS": [],
            "DJEMBES": []
        }

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        # Update rolling prices for ingredients from recent market trades.
        for product in self.prices_map:
            if product in state.market_trades and len(state.market_trades[product]) > 0:
                last_trade_price = state.market_trades[product][-1].price
                self.prices_map[product].append(last_trade_price)
                self.prices_map[product] = self.prices_map[product][-WINDOW_SIZE:]

        # Compute fair values and spreads for individual products.
        fair_values = {}
        spread_map = {}
        for product, recent_prices in self.prices_map.items():
            if product in ["CROISSANTS", "JAMS"]:
                fv = ewma(recent_prices, alpha=0.2)
                vol = rolling_std(recent_prices)
                sprd = 2 * vol
            elif product == "DJEMBES":
                fv, slope = linear_regression(recent_prices)
                vol = rolling_std(recent_prices)
                sprd = 2 * vol + 0.5 * abs(slope)
            else:
                fv = ewma(recent_prices)
                vol = rolling_std(recent_prices)
                sprd = 2 * vol
            fair_values[product] = fv
            spread_map[product] = max(1, sprd)

        # Compute intrinsic fair values for the baskets based on their compositions.
        # PICNIC_BASKET1 = 6 CROISSANTS + 3 JAMS + 1 DJEMBES
        basket1_fv = 6 * fair_values.get("CROISSANTS", 0) + 3 * fair_values.get("JAMS", 0) + 1 * fair_values.get(
            "DJEMBES", 0)
        # PICNIC_BASKET2 = 4 CROISSANTS + 2 JAMS
        basket2_fv = 4 * fair_values.get("CROISSANTS", 0) + 2 * fair_values.get("JAMS", 0)
        fair_values["PICNIC_BASKET1"] = basket1_fv
        fair_values["PICNIC_BASKET2"] = basket2_fv
        # Set basket spreads as a small fraction (e.g., 5%) of their intrinsic values.
        spread_map["PICNIC_BASKET1"] = max(1, 0.05 * basket1_fv)
        spread_map["PICNIC_BASKET2"] = max(1, 0.05 * basket2_fv)

        # For each product in the order book, generate bid/ask orders.
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            orders: List[Order] = []
            if product in ["CROISSANTS", "JAMS", "DJEMBES", "PICNIC_BASKET1", "PICNIC_BASKET2"]:
                fv = fair_values.get(product, 0)
                spread = spread_map.get(product, 1)
                bid_price = int(round(fv - spread / 2))
                ask_price = int(round(fv + spread / 2))
                current_pos = state.position.get(product, 0)
                base_size = compute_order_size(product,
                                               self.prices_map.get(product, [fv]),
                                               order_depth,
                                               current_pos,
                                               fv)
                available_buy = POSITION_LIMITS[product] - current_pos
                available_sell = POSITION_LIMITS[product] + current_pos
                buy_size = min(base_size, available_buy) if available_buy > 0 else 0
                sell_size = min(base_size, available_sell) if available_sell > 0 else 0
                if buy_size > 0:
                    orders.append(Order(product, bid_price, buy_size))
                if sell_size > 0:
                    orders.append(Order(product, ask_price, -sell_size))
                result[product] = orders
            else:
                result[product] = []

        # ------------------------------
        # Conversion Logic for Baskets
        # ------------------------------
        # If market prices for baskets deviate from their intrinsic values by 5% or more,
        # signal a conversion request.
        conversion_request: Dict[str, int] = {}
        conversion_limit = 5  # max units to convert per round

        # PICNIC_BASKET1 conversion evaluation.
        if "PICNIC_BASKET1" in state.order_depths:
            od = state.order_depths["PICNIC_BASKET1"]
            if od.buy_orders and od.sell_orders:
                best_bid = max(od.buy_orders.keys(), key=int)
                best_ask = min(od.sell_orders.keys(), key=int)
                basket_mid = (int(best_bid) + int(best_ask)) / 2.0
                intrinsic = basket1_fv
                if basket_mid < 0.95 * intrinsic:
                    conversion_request["PICNIC_BASKET1"] = conversion_limit  # Break basket to get ingredients.
                elif basket_mid > 1.05 * intrinsic:
                    conversion_request["PICNIC_BASKET1"] = -conversion_limit  # Combine ingredients into basket.

        # PICNIC_BASKET2 conversion evaluation.
        if "PICNIC_BASKET2" in state.order_depths:
            od = state.order_depths["PICNIC_BASKET2"]
            if od.buy_orders and od.sell_orders:
                best_bid = max(od.buy_orders.keys(), key=int)
                best_ask = min(od.sell_orders.keys(), key=int)
                basket_mid = (int(best_bid) + int(best_ask)) / 2.0
                intrinsic = basket2_fv
                if basket_mid < 0.95 * intrinsic:
                    conversion_request["PICNIC_BASKET2"] = conversion_limit
                elif basket_mid > 1.05 * intrinsic:
                    conversion_request["PICNIC_BASKET2"] = -conversion_limit

        traderData = jsonpickle.encode(self.prices_map)
        return result, conversion_request, traderData
