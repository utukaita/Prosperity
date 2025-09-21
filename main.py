from datamodel import Listing, OrderDepth, Trade, TradingState
import trader3
from typing import Dict
timestamp = 1100

listings = {
	"RAINFOREST_RESIN": Listing(
		symbol="RAINFOREST_RESIN",
		product="RAINFOREST_RESIN",
		denomination= "SEASHELLS"
	),
	"KELP": Listing(
		symbol="KELP",
		product="KELP",
		denomination= "SEASHELLS"
	),
	"SQUID_INK": Listing(
		symbol="SQUID_INK",
		product="SQUID_INK",
		denomination= "SEASHELLS"
	),
}

order_depths = {
	"RAINFOREST_RESIN": OrderDepth(
		buy_orders={10: 7, 9: 5},
		sell_orders={12: -5, 13: -3}
	),
	"SQUID_INK": OrderDepth(
		buy_orders={142: 3, 141: 5},
		sell_orders={144: -5, 145: -8}
	),
	"KELP": OrderDepth(
		buy_orders={80: 3, 82: 5},
		sell_orders={84: -5, 86: -8}
	),
}

own_trades = {
	"RAINFOREST_RESIN": [
		Trade(
			symbol="RAINFOREST_RESIN",
			price=11,
			quantity=4,
			buyer="SUBMISSION",
			seller="",
			timestamp=1000
		),
		Trade(
			symbol="RAINFOREST_RESIN",
			price=12,
			quantity=3,
			buyer="SUBMISSION",
			seller="",
			timestamp=1000
		)
	],
	"SQUID_INK": [
		Trade(
			symbol="SQUID_INK",
			price=143,
			quantity=2,
			buyer="",
			seller="SUBMISSION",
			timestamp=1000
		),
	],
	"KELP": [
		Trade(
			symbol="KELP",
			price=80,
			quantity=3,
			buyer="SUBMISSION",
				seller="",
			timestamp=1000
		),
	]
}

market_trades = {
	"RAINFOREST_RESIN": [],
	"SQUID_INK": [],
	"KELP": []
}

position = {
	"RAINFOREST_RESIN": 10,
	"SQUID_INK": -7,
	"KELP": 0
}

observations = {}
traderData = ""

state = TradingState(
	traderData,
	timestamp,
    listings,
	order_depths,
	own_trades,
	market_trades,
	position,
	observations
)
trader = trader3.Trader()
iterations = 100
for i in range(iterations):
  state.timestamp = i
  state.order_depths["RAINFOREST_RESIN"].buy_orders[10] = i
  state.order_depths["RAINFOREST_RESIN"].sell_orders[12] = -i
  state.order_depths["SQUID_INK"].buy_orders[142] = i
  state.order_depths["SQUID_INK"].sell_orders[144] = -i
  state.order_depths["KELP"].buy_orders[81] = i
  state.order_depths["KELP"].sell_orders[83] = -i
  print(state.position)
  trader.run(state)
  print("--------------------------------------------------")
