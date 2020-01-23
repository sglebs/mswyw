
def calc_mswyw(ms_runtime_data, formula_coefficients, overrides, default_value_for_missing_metric):
    # TODO: we still need to take into account how many "features" each microservices contributes with (value)
    # for now we only use the number of endpoints
    # we could infer function points from LOC based on Steve McConnel's material. But we have no place to get LOC.
    # if we let the user provide LOC, it is a pain for when we are run in multiple apps mode
    total_cost = 0.0
    total_value = 0.0
    for metrics in ms_runtime_data:
        total_cost += formula_coefficients["mem"]* overrides.get("mem", metrics.get("mem", default_value_for_missing_metric)) + \
                      formula_coefficients["cpu"]*overrides.get("cpu", metrics.get("cpu", default_value_for_missing_metric)) + \
                      formula_coefficients["epm"]*overrides.get("epm", metrics.get("epm", default_value_for_missing_metric))
        total_value += formula_coefficients["apdex"]*overrides.get("apdex", metrics.get("apdex", default_value_for_missing_metric)) + \
                       formula_coefficients["rpm"]*overrides.get("rpm", metrics.get("rpm", default_value_for_missing_metric)) + \
                       formula_coefficients["endpoints"]*overrides.get("endpoints", metrics.get("endpoints", default_value_for_missing_metric))
    if total_cost <= 0.0:
        return 0.0
    else:
        return formula_coefficients["total"] * (total_value / total_cost)