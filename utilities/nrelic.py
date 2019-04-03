# Provider module to fetch runtime data for an app from New Relic

import requests
from socket import error as SocketError
import xml.etree.ElementTree as ET

# Get instances: https://rpm.newrelic.com/api/explore/application_instances/list?application_id=nnnnnn
# Metric names: https://rpm.newrelic.com/api/explore/application_instances/names?instance_id=nnnnnnnn&application_id=nnnnnnnn


# These are the values we need in @extra_args
# "nrelic.APPID", "nrelic.APIKEY"
def compute_params(extra_args):
    app_id = extra_args["%s.APPID" % __name__]
    api_key = extra_args["%s.APIKEY" % __name__]
    app_instance_ids = _get_app_instance_ids(app_id, api_key)
    metric_dicts = [_get_app_instance_metrics(app_id, api_key, instance_id) for instance_id in app_instance_ids]
    return metric_dicts

def _get_app_instance_ids(app_id, api_key):
    url = "https://api.newrelic.com/v2/applications/%s/instances.json" % app_id
    newrelic_result = connect_and_get(url,api_key)
    json_reply = newrelic_result.json()
    return [instance["id"] for instance in json_reply["application_instances"]]


def _get_app_instance_metrics(app_id, api_key, instance_id):
    url = "https://api.newrelic.com/v2/applications/%s/instances/%s/metrics/data.xml?names[]=Memory/Physical&names[]=Apdex&names[]=CPU/User/Utilization&names[]=WebTransactionTotalTime&summarize=true" % (app_id,instance_id)
    newrelic_result = connect_and_get(url,api_key)
    root = ET.fromstring(newrelic_result.content)
    memory_usage = root.find(".//metrics/metric/[name='Memory/Physical']/timeslices/timeslice/values/used_bytes_by_host")
    apdex = root.find(".//metrics/metric/[name='Apdex']/timeslices/timeslice/values/score")
    cpu_percent = root.find(".//metrics/metric/[name='CPU/User/Utilization']/timeslices/timeslice/values/percent")
    rpm = root.find(".//metrics/metric/[name='WebTransactionTotalTime']/timeslices/timeslice/values//calls_per_minute")
    return {"mem":int(memory_usage.text), "apdex": float(apdex.text), "cpu": float(cpu_percent.text), "rpm": float(rpm.text)}

TIMEOUT=3 #seconds
def connect_and_get (url, api_key, verify=True, timeout=TIMEOUT):
    headers = {'X-Api-Key': api_key}
    return _get(url, headers=headers, verify=verify, timeout=timeout)

def _get (url, headers={}, verify=True, timeout=TIMEOUT):
    try:
        return requests.get(url, headers=headers, verify=verify, timeout=timeout)
    except requests.exceptions.ConnectionError as ce:
        raise ValueError("Can't fetch value")
    except SocketError as se:
        raise ValueError("Can't fetch value")
    except requests.exceptions.ReadTimeout as rt:
        raise ValueError("Can't fetch value")
    except requests.exceptions.ChunkedEncodingError as cee:
        raise ValueError("Can't fetch value")

