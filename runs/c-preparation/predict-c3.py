#!/usr/bin/env python3
"""在 C1 结束后、C3 开始前，以 C1 第 55 秒的 30 秒速率确定降额值。"""
import csv
import json
import math
from pathlib import Path
import urllib.parse
import urllib.request

with Path("runs/c1-stop/steps.csv").open(encoding="utf-8") as f:
    start = int(next(csv.DictReader(f))["start_unix"])
query = 'rate(cgroup_cpu_usage_seconds_total{job="instances"}[30s])'
params = {"query": query, "time": start + 55}
with urllib.request.urlopen("http://127.0.0.1:9090/api/v1/query?" + urllib.parse.urlencode(params)) as response:
    result = json.load(response)
assert result["status"] == "success"
prep = Path("runs/c-preparation")
(prep / "c1-cpu-baseline.json").write_text(json.dumps({"params": params, "response": result}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
usage = {x["metric"]["instance"]: float(x["value"][1]) for x in result["data"]["result"]}
u = usage["127.0.0.1:8101"]
quota = math.floor(u / 0.85 * 100 + 0.5)
lines = ["# C3 测前配额与预测", "", "在 C1 完成后、C3 开始前生成。", "", f"C1 起点 {start}；查询时刻为第 55 秒（Unix {start+55}），30 秒速率窗口位于首次注入之前。原始响应：`c1-cpu-baseline.json`。", "", f"PromQL：`{query}`。", "", "| 实例 | U（核） |", "|---|---|"]
lines += [f"| {addr} | {value:.9f} |" for addr, value in sorted(usage.items())]
lines += ["", f"C3 选择仍存活的 8101：U={u:.9f} 核，100×U/0.85={u/0.85*100:.6f}%，取整到 {quota}%。固定 160 请求/秒，约三分之一流量落到该实例，预计从 25% 降到 {quota}% 后在突发时更频繁耗尽周期预算，业务 p99 明显上升；`/readyz` 不做业务计算和连接池等待，预计默认健康检查仍通过。", "", "开启默认离群摘除后，预计最近 10 秒的真实请求 p99 超过其他实例中位数 3 倍且大于 50 ms 时，8101 会在几秒内被摘除 30 秒；再次加入后可能重复摘除，直到第 180 秒恢复配额。预计全站 p99 降低。最多同时摘除 1 台，剩余 2 台按容量线仍可承担 160 请求/秒，但负载集中会增加它们的尾延迟。"]
(prep / "c3-prediction.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
(prep / "quota.txt").write_text(str(quota)+"\n", encoding="utf-8")
print("\n".join(lines))
