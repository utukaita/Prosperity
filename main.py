from datamodel import Listing, OrderDepth, Trade, TradingState
import trader
from typing import Dict
timestamp = 1100

listings = {
	"PRODUCT1": Listing(
		symbol="PRODUCT1",
		product="PRODUCT1",
		denomination= "SEASHELLS"
	),
	"PRODUCT2": Listing(
		symbol="PRODUCT2",
		product="PRODUCT2",
		denomination= "SEASHELLS"
	),
}

order_depths = {
	"PRODUCT1": OrderDepth(
		buy_orders={10: 7, 9: 5},
		sell_orders={12: -5, 13: -3}
	),
	"PRODUCT2": OrderDepth(
		buy_orders={142: 3, 141: 5},
		sell_orders={144: -5, 145: -8}
	),
}

own_trades = {
	"PRODUCT1": [
		Trade(
			symbol="PRODUCT1",
			price=11,
			quantity=4,
			buyer="SUBMISSION",
			seller="",
			timestamp=1000
		),
		Trade(
			symbol="PRODUCT1",
			price=12,
			quantity=3,
			buyer="SUBMISSION",
			seller="",
			timestamp=1000
		)
	],
	"PRODUCT2": [
		Trade(
			symbol="PRODUCT2",
			price=143,
			quantity=2,
			buyer="",
			seller="SUBMISSION",
			timestamp=1000
		),
	]
}

market_trades = {
	"PRODUCT1": [],
	"PRODUCT2": []
}

position = {
	"PRODUCT1": 10,
	"PRODUCT2": -7
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
trader = trader.Trader()
iterations = 3
for i in range(iterations):
  state.timestamp = i
  state.order_depths["PRODUCT1"].buy_orders[10] = i
  state.order_depths["PRODUCT1"].sell_orders[12] = -i
  state.order_depths["PRODUCT2"].buy_orders[142] = i
  state.order_depths["PRODUCT2"].sell_orders[144] = -i
  trader.run(state)
  print("--------------------------------------------------")
