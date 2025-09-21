import math

COEF = 10_000
percentages = {0: 10, 1: 10, 2: 10, 3: 10, 4: 10, 5: 10, 6: 10, 7: 10, 8: 10, 9: 10}
yields = {0: 10, 1: 80, 2: 37, 3: 17, 4: 90, 5: 31, 6: 50, 7: 20, 8: 73, 9: 89}
inhabitants = {0: 1, 1: 6, 2: 3, 3: 1, 4: 10, 5: 2, 6: 4, 7: 2, 8: 4, 9: 8}

def change_percentages(percentages, new_values):
    old_sum = 0
    new_sum = 0
    for index, value in new_values.items():
        old_sum += percentages[index]
        percentages[index] = value
        new_sum += percentages[index]
    if new_sum > 101:
        raise ValueError("The inputted percentages have a sum greater than 100")
    if new_sum <= 0:
        raise ValueError("The inputted percentages have a sum less than or equal to 0")
    for index, value in percentages.items():
        percentages[index] = (value / (new_sum)) * 100
    assert math.isclose(sum(list(percentages.values())), 100, rel_tol=1e-9), "The sum of the percentages is not equal to 100"
    return percentages

n = 100
values_log = []
for i in range(n):
    values = {i : yields[i] * COEF / (inhabitants[i]+percentages[i]) for i in range(10)}
    values_log.append(values)
    print("Values: ", values)
    values_sum = sum(list(values.values()))
    new_percentages = {i : (values[i] / values_sum * 100) for i in range(10)}
    percentages = change_percentages(percentages, new_percentages)
    print("Percentages: ", percentages)

average_values = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0}
for d in values_log[n//2:]:
    for i in range(10):
        average_values[i] += d[i]
for i in range(10):
    average_values[i] /= (n//2)
print("Average values: ", average_values)
print("Final values: ", values)

