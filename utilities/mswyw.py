"""Microservice worth your weight.

Usage:
  mswyw     --codeInfoProvider=<fqnOrJsonOrJsonPath> \r\n \
            [--providerParams=<fqnOrJsonOrJsonPath>] \r\n \
            [--runtimeProvider=<fqnOrJsonOrJsonPath>] \r\n \
            [--coefficients=<json>]


Options:
  --runtimeProvider=<fqnOrJsonOrJsonPath>    Where to get runtime metrics. Either a fully qualified name of a python module or a json literal or json file. [default: nrelic]
  --codeInfoProvider=<fqnOrJsonOrJsonPath>   Where to get code metrics. Either a fully qualified name of a python module or a json literal or json file.
  --providerParams=<fqnOrJsonOrJsonPath>     Custom parameters to the providers used. [default: {}]
  --coefficients=<json>                      Custom formula coefficients [default: {"endpoints":100.0,"mem":1.0,"cpu":1000.0,"apdex":1000.0,"rpm":1000.0,"epm":100.0,"total":1000.0}]


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

# Adapted (added file): https://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
URL_REGEX = re.compile(
        r'^(?:http|ftp|file)s?://', re.IGNORECASE)


def is_url(a_string):
    return URL_REGEX.match(a_string)


def params_as_dict(fqnOrJsonOrJsonPath, extra_args):
    if os.path.isfile(fqnOrJsonOrJsonPath):
        with open(fqnOrJsonOrJsonPath) as input:
            return json.load(input)
    elif is_url(fqnOrJsonOrJsonPath):
        with urllib.request.urlopen(fqnOrJsonOrJsonPath) as url_connection:
            return json.loads(url_connection.read().decode('utf-8'))
    else:
        try:  #literal json?
            return json.loads(fqnOrJsonOrJsonPath)
        except ValueError:
            try:  # fully qualified name of python module?
                provider_module = importlib.import_module(fqnOrJsonOrJsonPath)
            except ModuleNotFoundError:
                raise ValueError("Cannot resolve %s" % fqnOrJsonOrJsonPath)
            return provider_module.compute_params(extra_args)

def calc_mswyw(ms_runtime_data, ms_code_info_data, formula_coefficients):
    #TODO: we still need to take into account how many "features" each microservices contributes with (value)
    #we could infer function points from LOC based on Steve McConnel's material. Or let the user override
    total_cost = 0.0
    total_value = 0.0
    for metrics in ms_runtime_data:
        total_cost += formula_coefficients["mem"]*metrics["mem"] + formula_coefficients["cpu"]*metrics["cpu"] + formula_coefficients["epm"]*metrics["epm"]
        total_value += formula_coefficients["apdex"]*metrics["apdex"] + formula_coefficients["rpm"]*metrics["rpm"] + formula_coefficients["endpoints"]*metrics["endpoints"]
    return formula_coefficients["total"] * (total_value / total_cost)


def main():
    start_time = datetime.datetime.now()
    arguments = docopt(__doc__, version=VERSION)
    print("\r\n====== mswyw by Marcio Marchini: marcio@BetterDeveloper.net ==========")
    print(arguments)
    try:
        formula_coefficients = json.loads(arguments.get("--coefficients", "{}"))
        provider_params = params_as_dict(arguments.get("--providerParams", {}),"")
        ms_runtime_data = params_as_dict(arguments.get("--runtimeProvider"), provider_params)
        ms_code_info_data = params_as_dict(arguments.get("--codeInfoProvider"), provider_params)
        mswyw_score = calc_mswyw(ms_runtime_data, ms_code_info_data, formula_coefficients)
    except ValueError as e:
        print("Problem: %s" % repr(e))
        exit(-1)
    end_time = datetime.datetime.now()
    print("\r\n--------------------------------------------------")
    print("\r\nInstances:\r\n %s" % ms_runtime_data)
    print("\r\n--------------------------------------------------")
    print("Started : %s" % str(start_time))
    print("Finished: %s" % str(end_time))
    print("Total: %s" % str(end_time-start_time))
    print("mswyw score: %s" % str(mswyw_score))
    print("--------------------------------------------------")

if __name__ == '__main__':
    main()