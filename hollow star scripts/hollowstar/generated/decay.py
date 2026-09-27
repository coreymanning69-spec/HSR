def resolve(inputs):
    elapsed = inputs["elapsed"]
    potency = inputs["potency"]
    rate = inputs["rate"]
    model = inputs["model"]
    value = potency
    if model == "linear":
        value = potency - rate * elapsed
    if model == "exponential":
        value = potency * exp(-rate * elapsed)
    if model == "logarithmic":
        value = potency - rate * log1p(elapsed)
    if model == "threshold":
        value = 0 if elapsed >= rate else potency
    value = max(0, value)
    if inputs["rounding"] == "floor":
        value = floor(value)
    if inputs["rounding"] == "ceil":
        value = ceil(value)
    if inputs["rounding"] == "nearest":
        value = floor(value + 0.5)
    return {"potency": value}
