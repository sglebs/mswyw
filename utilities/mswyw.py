"""Microservice worth your weight.

Usage:
  mswyw     --providerParams=<fqnOrJsonOrJsonPath> \r\n \
            [--runtimeProvider=<fqnOrJsonOrJsonPath>] \r\n \
            [--coefficients=<json>] \r\n \
            [--interval=<integer>]


Options:
  --runtimeProvider=<fqnOrJsonOrJsonPath>    Where to get runtime metrics. Either a fully qualified name of a python module or a json literal or json file. [default: nrelic]
  --providerParams=<fqnOrJsonOrJsonPath>     Custom parameters to the providers used. [default: {}]
  --coefficients=<json>                      Custom formula coefficients [default: {"endpoints":100.0,"mem":1.0,"cpu":1000.0,"apdex":1000.0,"rpm":1000.0,"epm":100.0,"total":1000.0}]
  --interval=<integer >                      Interval in minutes for the sampling [default: 30]


Author:
  Marcio Marchini (marcio@BetterDeveloper.net)

"""
import datetime
import json
import os.path
import urllib
import re
from docopt import docopt
from utilities import VERSION
import importlib

# Adapted: https://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
URL_REGEX = re.compile(
        r'^(?:http|ftp|file)s?://', re.IGNORECASE)

DEFAULT_INTERVAL_IN_MINUTES=30

def is_url(a_string):
    return URL_REGEX.match(a_string)


def params_as_dict(fqn_or_json_orjson_path):
    if os.path.isfile(fqn_or_json_orjson_path):
        with open(fqn_or_json_orjson_path) as input_file:
            return json.load(input_file)
    elif is_url(fqn_or_json_orjson_path):
        with urllib.request.urlopen(fqn_or_json_orjson_path) as url_connection:
            return json.loads(url_connection.read().decode('utf-8'))
    else:
        return json.loads(fqn_or_json_orjson_path)


def compute_metrics(plugin_name_as_fqn_python_module, plugin_specific_extra_args, interval_in_minutes):
    try:
        provider_module = importlib.import_module(plugin_name_as_fqn_python_module)
    except ModuleNotFoundError:
        raise ValueError("Cannot resolve %s" % plugin_name_as_fqn_python_module)
    return provider_module.compute_metrics(plugin_specific_extra_args, interval_in_minutes)


def calc_mswyw(ms_runtime_data, formula_coefficients):
    # TODO: we still need to take into account how many "features" each microservices contributes with (value)
    # for now we only use the number of endpoints
    # we could infer function points from LOC based on Steve McConnel's material. But we have no place to get LOC.
    # if we let the user provide LOC, it is a pain for when we are run in multiple apps mode
    total_cost = 0.0
    total_value = 0.0
    for metrics in ms_runtime_data:
        total_cost += formula_coefficients["mem"]*metrics["mem"] + \
                      formula_coefficients["cpu"]*metrics["cpu"] + \
                      formula_coefficients["epm"]*metrics["epm"]
        total_value += formula_coefficients["apdex"]*metrics["apdex"] + \
                       formula_coefficients["rpm"]*metrics["rpm"] + \
                       formula_coefficients["endpoints"]*metrics["endpoints"]
    if total_cost <= 0.0:
        return 0.0
    else:
        return formula_coefficients["total"] * (total_value / total_cost)


def sanitize_coefficients(coefs):
    for name in ["total", "apdex", "rpm", "endpoints", "mem", "cpu", "epm"]:
        if name not in coefs:
            raise ValueError("Missing coefficient %s" % name)
    for name, value in coefs.items():
        try:
            float(value)
        except ValueError:
            raise ValueError("%s is set to %s, which is not a valid number" % (name, value))


def main():
    start_time = datetime.datetime.now()
    arguments = docopt(__doc__, version=VERSION)
    print("\r\n====== mswyw - see https://github.com/sglebs/mswyw ==========")
    print(arguments)
    try:
        formula_coefficients = json.loads(arguments.get("--coefficients", "{}"))
        sanitize_coefficients(formula_coefficients)
        provider_params = params_as_dict(arguments.get("--providerParams", {}))
        interval_in_minutes = params_as_dict(arguments.get("--interval"))
        ms_runtime_data = compute_metrics(arguments.get("--runtimeProvider"), provider_params, interval_in_minutes)
        mswyw_score = calc_mswyw(ms_runtime_data, formula_coefficients)
        end_time = datetime.datetime.now()
        print("\r\n--------------------------------------------------")
        print("\r\nInstances:")
        for runtime_data in ms_runtime_data:
            print(runtime_data)
        print("\r\n--------------------------------------------------")
        print("Started : %s" % str(start_time))
        print("Finished: %s" % str(end_time))
        print("Total: %s" % str(end_time - start_time))
        print("mswyw score: %s" % str(mswyw_score))
        print("--------------------------------------------------")
    except ValueError as e:
        print("Problem: %s" % repr(e))
        exit(-1)


if __name__ == '__main__':
    main()
