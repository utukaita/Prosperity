
priceMatrix = [[1, 1.45, 0.52, 0.72],
               [0.7, 1, 0.31, 0.48],
               [1.95, 3.1, 1, 1.49],
               [1.34, 1.98, 0.64, 1]]

indexDict = {0: "Snowballs", 1: "Pizza's", 2: "Silicon Nuggets", 3: "SeaShells"}
BASE = "SeaShells"
BASE_KEY = next((k for k, v in indexDict.items() if v == BASE), None)

MATRIX_SIZE = len(priceMatrix)
MAX_TRADES = 5

# Top down dynamic programming approach
# Possible to implement advanced backtracking features

def get_max_profit(trade_count, base, target, memo=None):
    if memo is None:
        memo = {}
    if trade_count == 1:
        return priceMatrix[base][target], [(indexDict[base], indexDict[target])]
    max_profit = 0
    max_trade = []
    for i in range(MATRIX_SIZE):
            if (trade_count - 1, i, target) in memo:
                recursive_max_profit, recursive_max_trade = memo[(trade_count - 1, i, target)]
            else:
                recursive_max_profit, recursive_max_trade = get_max_profit(trade_count - 1, i, target, memo)
                memo[(trade_count - 1, i, target)] = (recursive_max_profit, recursive_max_trade)
            current_profit = priceMatrix[base][i] * recursive_max_profit
            if current_profit > max_profit:
                max_profit = current_profit
                max_trade = [(indexDict[base], indexDict[i])] + recursive_max_trade
    return max_profit, max_trade

profit, trade = get_max_profit(MAX_TRADES, BASE_KEY, BASE_KEY)

print("Max profit: ", profit)
# Max profit:  1.0886803200000001

print("Trade sequence: ", trade)
# Trade sequence:  [('SeaShells', 'Snowballs'), ('Snowballs', 'Silicon Nuggets'), ('Silicon Nuggets', "Pizza's"), ("Pizza's", 'Snowballs'), ('Snowballs', 'SeaShells')]

# Brute force approach to check the result
# max = 0
# trade = []
# for i in range(4):
#     for j in range(4):
#         for k in range(4):
#             for l in range(4):
#                 p = priceMatrix[BASE_KEY][i] * priceMatrix[i][j] * priceMatrix[j][k] * priceMatrix[k][l] * priceMatrix[l][BASE_KEY]
#                 if p > max:
#                     max = p
#                     trade = [(indexDict[BASE_KEY], indexDict[i]), (indexDict[i], indexDict[j]), (indexDict[j], indexDict[k]), (indexDict[k], indexDict[l]), (indexDict[l], indexDict[BASE_KEY])]
#
# print("Max profit: ", max)
# print("Trade sequence: ", trade)