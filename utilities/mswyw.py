"""Microservice worth your weight.

Usage:
  mswyw     --providerParams=<fqnOrJsonOrJsonPath> \r\n \
            [--runtimeProvider=<fqnOrJsonOrJsonPath>] \r\n \
            [--calcProvider=<fqn>] \r\n \
            [--coefficients=<json>] \r\n \
            [--overrides=<json>] \r\n \
            [--interval=<integer>]\r\n \
            [--endMinutesAgo=<integer>]


Options:
  --runtimeProvider=<fqnOrJsonOrJsonPath>    Where to get runtime metrics. Either a fully qualified name of a python module or a json literal or json file. [default: nrelic]
  --calcProvider=<fqn>                       Python module to use which has the formula which computes teh score. [default: formula]
  --providerParams=<fqnOrJsonOrJsonPath>     Custom parameters to the providers used. [default: {}]
  --coefficients=<json>                      Custom formula coefficients [default: {"endpoints":100.0,"mem":1.0,"cpu":1000.0,"apdex":1000.0,"rpm":1000.0,"epm":100.0,"total":1000.0}]
  --interval=<integer>                       Interval in minutes for the sampling [default: 30]
  --endMinutesAgo=<integer>                  How many minutes ago (from now) the sampling interval ends. now=0, 1h ago=60, etc. [default: 0]
  --overrides=<json>                         Values to use in the formula instead of values measures. Useful for apdex on latforms without it. [default: {}]

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
DEFAULT_END_MINUTES_AGO=0
DEFAULT_VALUE_FOR_MISSING_MATRIC = -1000

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


def compute_metrics(plugin_name_as_fqn_python_module, plugin_specific_extra_args, start_time, end_time):
    try:
        provider_module = importlib.import_module(plugin_name_as_fqn_python_module)
    except ModuleNotFoundError:
        raise ValueError("Cannot resolve %s" % plugin_name_as_fqn_python_module)
    return provider_module.compute_metrics(plugin_specific_extra_args, start_time, end_time)


def compute_formula(plugin_name_as_fqn_python_module, ms_runtime_data, formula_coefficients, overrid):
    try:
        calc_module = importlib.import_module(plugin_name_as_fqn_python_module)
    except ModuleNotFoundError:
        raise ValueError("Cannot resolve %s" % plugin_name_as_fqn_python_module)
    return calc_module.calc_mswyw(ms_runtime_data, formula_coefficients, overrid, DEFAULT_VALUE_FOR_MISSING_MATRIC)


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
    script_start_time = datetime.datetime.now()
    arguments = docopt(__doc__, version=VERSION)
    print("\r\n====== mswyw - see https://github.com/sglebs/mswyw ==========")
    print(arguments)
    try:
        formula_coefficients = json.loads(arguments.get("--coefficients", "{}"))
        sanitize_coefficients(formula_coefficients)
        provider_params = params_as_dict(arguments.get("--providerParams", {}))
        interval_in_minutes = int (params_as_dict(arguments.get("--interval", DEFAULT_INTERVAL_IN_MINUTES)))
        end_minutes_ago = int (params_as_dict(arguments.get("--endMinutesAgo", DEFAULT_END_MINUTES_AGO)))
        sampling_end_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=end_minutes_ago)
        sampling_start_time = sampling_end_time - datetime.timedelta(minutes=interval_in_minutes)
        ms_runtime_data = compute_metrics(arguments.get("--runtimeProvider"), provider_params, sampling_start_time, sampling_end_time)
        overrides = json.loads(arguments.get("--overrides", "{}"))
        mswyw_score = compute_formula(arguments.get("--calcProvider"), ms_runtime_data, formula_coefficients, overrides)
        script_end_time = datetime.datetime.now()
        print("\r\n--------------------------------------------------")
        print("Sampling Start time: %sZ" % sampling_start_time.isoformat())
        print("Sampling End time:   %sZ" % sampling_end_time.isoformat())
        print("Instances:")
        for runtime_data in ms_runtime_data:
            print(runtime_data)
        print("\r\n--------------------------------------------------")
        print("Started : %s" % str(script_start_time))
        print("Finished: %s" % str(script_end_time))
        print("Total: %s" % str(script_end_time - script_start_time))
        print("mswyw score: %s" % str(mswyw_score))
        print("--------------------------------------------------")
    except ValueError as e:
        print("Problem: %s" % repr(e))
        exit(-1)


if __name__ == '__main__':
    main()
