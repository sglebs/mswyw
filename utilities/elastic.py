from elasticsearch import Elasticsearch
import datetime
import json

DEFAULT_APDEX_T = 0.5  # seconds

# These are the values we need in @plugin_specific_extra_args
# "elastic.URL", "elastic.USER", "elastic.PASSWORD", "elastic.APPS", "elastic.APDEX_T"
def compute_metrics(plugin_specific_extra_args, start_time, end_time):
    base_url = plugin_specific_extra_args.get("%s.URL" % __name__, "")
    user = plugin_specific_extra_args.get("%s.USER" % __name__, "")
    password = plugin_specific_extra_args.get("%s.PASSWORD" % __name__, "")
    app_names = plugin_specific_extra_args.get("%s.APPS" % __name__, "")
    apdex_t = plugin_specific_extra_args.get("%s.APDEX_T" % __name__, DEFAULT_APDEX_T)
    if len(app_names) == 0:
        raise ValueError("No Apps found under the parameters provided: %s" % app_names)
    result = []
    es = Elasticsearch([base_url], http_auth=(user, password))
    performance_search = es.search(index="apm-*", body=_get_cpu_ram_performance_query_as_dict(start_time, end_time, app_names))
    result.extend(_extract_memory_and_cpu_usage_from_charts_data(performance_search))

    metrics_search = es.search(index="apm-*", body=_get_tpm_epm_apdex_query_as_dict(start_time, end_time, app_names, apdex_t))
    interval_in_minutes = (end_time - start_time).seconds / 60
    tpm_data = _extract_tpm_from_metrics_search(metrics_search, interval_in_minutes)

    for service_info in result:
        tpm_data_for_container = tpm_data [service_info["_container_id"]]
        service_info.update(tpm_data_for_container)
    return result

def _extract_tpm_from_metrics_search(metrics_search, interval_in_minutes):
    result = {}
    for service_ínfo_dict in metrics_search["aggregations"]["service_name"]["buckets"]:
        for container_info_dict in service_ínfo_dict["container_id"]["buckets"]:
            service_name = service_ínfo_dict['key']
            apdex_avg = container_info_dict['apdex_avg']['value']
            endpoints_count = container_info_dict['trans_name_count']['value']
            error_ount = container_info_dict['error_count']['value']
            epm = error_ount / interval_in_minutes
            trans_id_count = container_info_dict['trans_id_count']['value']
            tpm = trans_id_count / interval_in_minutes
            #trans_duration_avg_us = container_info_dict['trans_duration_avg_us']['value']
            container_id = container_info_dict["key"]
            result[container_id] = {"endpoints": endpoints_count,
                           "apdex": apdex_avg,
                           "rpm": float(tpm),
                           "epm": float(epm),
                           "_container_id": container_id,
                           "_appname": service_name}

    return result


def _extract_memory_and_cpu_usage_from_charts_data(performance_search):
    result = []
    for service_ínfo_dict in performance_search["aggregations"]["service_name"]["buckets"]:
        for perf_by_container in service_ínfo_dict["host_name"]["buckets"]:
            service_data = dict()
            service_data["_container_id"] = perf_by_container["key"]
            service_data["mem"] = perf_by_container["ram_used"]["value"]
            service_data["cpu"] = perf_by_container["cpu_percent_max"]["value"] * 100 # equivalent to the system max in the Kibana GUI
            result.append(service_data)
    return result


def _get_cpu_ram_performance_query_as_dict (start_time, end_time, app_names):
    global QUERY_TEMPLATE_FOR_CPU_RAM
    concrete_query = QUERY_TEMPLATE_FOR_CPU_RAM  % (app_names , start_time.isoformat(), end_time.isoformat())
    return json.loads(concrete_query)


def _get_tpm_epm_apdex_query_as_dict (start_time, end_time, app_names, apdex_t):
    global QUERY_TEMPLATE_FOR_TPM_EPM
    concrete_query = QUERY_TEMPLATE_FOR_TPM_EPM % (apdex_t, apdex_t, app_names, start_time.isoformat(), end_time.isoformat())
    return json.loads(concrete_query)


QUERY_TEMPLATE_FOR_CPU_RAM = \
    """
{
  "aggs": {
    "service_name": {
      "terms": {
        "field": "service.name",
        "order": {
          "_key": "desc"
        },
        "size": 999
      },
      "aggs": {
        "host_name": {
          "terms": {
            "field": "container.id",
            "order": {
              "_key": "desc"
            },
            "size": 999
          },
          "aggs": {
            "cpu_percent_avg": {
              "avg": {
                "field": "system.process.cpu.total.norm.pct"
              }
            },
            "ram_avg": {
              "avg": {
                "field": "system.process.memory.size"
              }
            },
            "ram_max": {
              "max": {
                "field": "system.process.memory.size"
              }
            },
            "ram_used": {
              "max": {
                "field": "system.process.memory.rss.bytes"
              }
            },
            "cpu_percent_max": {
              "max": {
                "field": "system.process.cpu.total.norm.pct"
              }
            }
          }
        }
      }
    }
  },
  "size": 0,
  "_source": {
    "excludes": []
  },
  "stored_fields": [
    "*"
  ],
  "script_fields": {},
  "docvalue_fields": [
    {
      "field": "@timestamp",
      "format": "date_time"
    },
    {
      "field": "event.created",
      "format": "date_time"
    },
    {
      "field": "event.end",
      "format": "date_time"
    },
    {
      "field": "event.start",
      "format": "date_time"
    },
    {
      "field": "file.accessed",
      "format": "date_time"
    },
    {
      "field": "file.created",
      "format": "date_time"
    },
    {
      "field": "file.ctime",
      "format": "date_time"
    },
    {
      "field": "file.mtime",
      "format": "date_time"
    },
    {
      "field": "process.start",
      "format": "date_time"
    }
  ],
  "query": {
    "bool": {
      "must": [],
      "filter": [
        {
          "match_all": {}
        },
        {
          "match_phrase": {
            "service.name": {
              "query": "%s"
            }
          }
        },                
        {
          "range": {
            "@timestamp": {
              "format": "strict_date_optional_time",
              "gte": "%sZ",
              "lte": "%sZ"
            }
          }
        }
      ],
      "should": [],
      "must_not": []
    }
  }
}
        """

QUERY_TEMPLATE_FOR_TPM_EPM = \
    """
{
    "aggs": {
        "service_name": {
            "terms": {
                "field": "service.name",
                "size": 1000
            },
            "aggs": {
                "container_id": {
                    "terms": {
                        "field": "container.id"
                    },
                    "aggs": {
                        "trans_duration_avg_us": {
                            "avg": {
                                "field": "transaction.duration.us"
                            }
                        },
                        "3": {
                            "percentiles": {
                                "field": "transaction.duration.us",
                                "percents": [
                                    95
                                ],
                                "keyed": false
                            }
                        },
                        "trans_id_count": {
                            "cardinality": {
                                "field": "transaction.id"
                            }
                        },
                        "error_count": {
                            "cardinality": {
                                "field": "error.id"
                            }
                        },
                        "apdex_avg": {
                            "avg": {
                                "script": {
                                    "source": "if((!doc['transaction.duration.us'].empty)&&(doc['transaction.duration.us'].size()>0)) { def apdex_t = %s * 1000000; if(doc['transaction.duration.us'].value<=apdex_t) return 1; else if (doc['transaction.duration.us'].value <= (apdex_t * 4)) return 0.5; else return 0;} else return null;",
                                    "lang": "painless"
                                }
                            }
                        },
                        "trans_name_count": {
                            "cardinality": {
                                "field": "transaction.name"
                            }
                        }
                    }
                }
            }
        }
    },
    "size": 0,
    "_source": {
        "excludes": []
    },
    "stored_fields": [
        "*"
    ],
    "script_fields": {
        "apdex": {
            "script": {
                "source": "if((!doc['transaction.duration.us'].empty)&&(doc['transaction.duration.us'].size()>0)) { def apdex_t = %s * 1000000; if(doc['transaction.duration.us'].value<=apdex_t) return 1; else if (doc['transaction.duration.us'].value <= (apdex_t * 4)) return 0.5; else return 0;} else return null;",
                "lang": "painless"
            }
        }
    },
    "docvalue_fields": [
        {
            "field": "@timestamp",
            "format": "date_time"
        },
        {
            "field": "event.created",
            "format": "date_time"
        },
        {
            "field": "event.end",
            "format": "date_time"
        },
        {
            "field": "event.start",
            "format": "date_time"
        },
        {
            "field": "file.accessed",
            "format": "date_time"
        },
        {
            "field": "file.created",
            "format": "date_time"
        },
        {
            "field": "file.ctime",
            "format": "date_time"
        },
        {
            "field": "file.mtime",
            "format": "date_time"
        },
        {
            "field": "process.start",
            "format": "date_time"
        }
    ],
    "query": {
        "bool": {
            "must": [
                {
                    "match_all": {}
                }
            ],
            "filter": [
                {
                    "match_phrase": {
                        "service.name": {
                            "query": "%s"
                        }
                    }
                },
                {
                    "match_phrase": {
                        "transaction.type": {
                            "query": "request"
                        }
                    }
                },
                {
                    "range": {
                        "@timestamp": {
                            "format": "strict_date_optional_time",
                            "gte": "%sZ",
                            "lte": "%sZ"
                        }
                    }
                }
            ],
            "should": [],
            "must_not": []
        }
    }
}
    """
