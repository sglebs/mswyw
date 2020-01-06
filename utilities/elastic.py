import requests
from requests.auth import HTTPBasicAuth
from socket import error as SocketError
import json
#from elasticsearch import Elasticsearch
import datetime
TIMEOUT=4 #seconds

# These are the values we need in @plugin_specific_extra_args
# "elastic.URL", "elastic.USER", "elastic.PASSWORD", "elastic.APPS"
def compute_metrics(plugin_specific_extra_args):
    base_url = plugin_specific_extra_args.get("%s.URL" % __name__, "")
    user = plugin_specific_extra_args.get("%s.USER" % __name__, "")
    password = plugin_specific_extra_args.get("%s.PASSWORD" % __name__, "")
    app_names = plugin_specific_extra_args.get("%s.APPS" % __name__, "").split(",")
    if len(app_names) == 0:
        raise ValueError("No Apps found under the parameters provided: %s" % app_names)
    end_time = datetime.datetime.now() #utcnow() ?
#    current_time = datetime.datetime.now(datetime.timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=30)
#    es = Elasticsearch([base_url], http_auth=(user, password), timeout=TIMEOUT)
#    es.cluster.health(wait_for_status='yellow', request_timeout=TIMEOUT)
#    search = es.search(index='test-index', filter_path=['hits.hits._id', 'hits.hits._type'], request_timeout=TIMEOUT)
    result = []
    for app_name in app_names:
        metrics = _get_app_instance_metrics(base_url, user, password, app_name, start_time, end_time)
        metrics["_appname"] = app_name
        result.append(metrics)
    return result

def _extract_cpu_usage_from_series(series_array):
    result = 0.0
    for series in series_array:
        if series["key"] == "processCPUMax":
            result = series["overallValue"]
    return result * 100 if result is not None else 0  # *100 to percentage as 0...100

def _extract_memory_usage_from_series(series_array):
    result = 0.0
    for series in series_array:
        if series["key"] == "memoryUsedMax":
            result = series["overallValue"]
    return result * 1024 * 1024 * 1024 if result is not None else 0  # from float GB to bytes

def _extract_memory_and_cpu_usage_from_charts_data(charts_dict):
    charts = charts_dict["charts"]
    cpu_usage = 0.0
    mem_usage = 0.0
    for chart in charts:
        if chart["key"] == "cpu_usage_chart":
            cpu_usage = _extract_cpu_usage_from_series (chart["series"])
        if chart["key"] == "memory_usage_chart":
            mem_usage = _extract_memory_usage_from_series(chart["series"])
    return [cpu_usage, mem_usage]

def _extract_agent_rpm_epm_from_requests_data(perf_data_dict):
    perf_data = perf_data_dict["items"]
    if len(perf_data) <= 0:
        raise ValueError("No RPM & EPM data available for app")
    perf_data = perf_data[0]
    return [perf_data["agentName"], perf_data["transactionsPerMinute"], perf_data["errorsPerMinute"]]

def _get_app_instance_metrics(base_url, user, password, app_name, start_time, end_time):
    url = r'%s?start=%s&end=%s&uiFilters={"kuery":"transaction.type : \"request\" and service.name : \"%s\""}' % (base_url, start_time.isoformat(), end_time.isoformat(), app_name)
    request_performance_response = connect_and_get (url, user, password)
    if not request_performance_response.ok:
        raise ValueError("Response error opening %s" % url)
    request_performance_dict = json.loads(request_performance_response.content)
    agent, rpm, epm = _extract_agent_rpm_epm_from_requests_data (request_performance_dict)

    url = "%s/%s/metrics/charts?start=%s&end=%s&agentName=%s&uiFilters=" % (base_url, app_name, start_time.isoformat(), end_time.isoformat(), agent)
    charts_response = connect_and_get (url, user, password)
    if not charts_response.ok:
        raise ValueError("Response error opening %s" % url)
    charts_dict = json.loads(charts_response.content)
    cpu , memory = _extract_memory_and_cpu_usage_from_charts_data (charts_dict)

    url = r'%s/%s/transaction_groups?start=%s&end=%s&transactionType=request&uiFilters={"kuery":"transaction.type : \"request\""}' % (base_url, app_name, start_time.isoformat(), end_time.isoformat())
    transations_response = connect_and_get (url, user, password)
    if not transations_response.ok:
        raise ValueError("Response error opening %s" % url)
    transations_list = json.loads(transations_response.content)


    return {"mem":int(memory),
            "endpoints": len(transations_list),
            "apdex": 0, # TODO
            "cpu": float(cpu),
            "rpm": float(rpm),
            "epm": float(epm),
            "_lang": agent
            }



def connect_and_get (url, user, password, verify=True, timeout=TIMEOUT):
    auth = HTTPBasicAuth(user, password)
    return _get(url, auth, verify=verify, timeout=timeout)

def _get (url, auth, verify=True, timeout=TIMEOUT):
    try:
        return requests.get(url, auth=auth, verify=verify, timeout=timeout)
    except requests.exceptions.ConnectionError as ce:
        raise ValueError("Connection error opening %s" % url)
    except SocketError as se:
        raise ValueError("Socket error opening %s" % url)
    except requests.exceptions.ReadTimeout as rt:
        raise ValueError("Read timeout opening %s" % url)
    except requests.exceptions.ChunkedEncodingError as cee:
        raise ValueError("Encoding error opening %s" % url)

