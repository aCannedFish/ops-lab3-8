#!/usr/bin/env python3
"""保存单轮任务 C 的 Prometheus 原始响应，时间来自 loadgen 的 steps.csv。"""
import csv
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

run = Path("runs") / sys.argv[1]
with (run / "steps.csv").open(encoding="utf-8") as f:
    step = next(csv.DictReader(f))
start = float(step["start_unix"])
end = float(step["end_unix"])
queries = {
    "cpu_cores": 'rate(cgroup_cpu_usage_seconds_total{job="instances"}[30s])',
    "quota_cores": 'cgroup_cpu_limit_cores{job="instances"}',
    "throttle_ratio": 'rate(cgroup_cpu_throttled_periods_total{job="instances"}[30s]) / rate(cgroup_cpu_periods_total{job="instances"}[30s])',
    "backend_p99_seconds": 'histogram_quantile(0.99, sum by (backend, le) (rate(lb_request_duration_seconds_bucket[30s])))',
    "backend_up": "lb_backend_up",
    "backend_eligible": "lb_backend_eligible",
}
saved = {}
for name, query in queries.items():
    params = {"query": query, "start": start, "end": end, "step": 5}
    url = "http://127.0.0.1:9090/api/v1/query_range?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as response:
        result = json.load(response)
    assert result["status"] == "success", result
    saved[name] = {"params": params, "response": result}
(run / "prometheus-range.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(run / "prometheus-range.json")
