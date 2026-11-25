#!/usr/bin/env python3
"""只读取原始输出，生成任务 C 对照表；不修改 run3.sh 产生的文件。"""
import csv
import json
import math
from pathlib import Path
import statistics

root = Path("runs")
names = ["c1-stop", "c2-default", "c2-sensitive", "c3-slow", "c3-outlier"]


def rows(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def intervals(seconds):
    groups = []
    for second in seconds:
        if groups and second == groups[-1][-1] + 1:
            groups[-1].append(second)
        else:
            groups.append([second])
    return "、".join(f"[{g[0]}, {g[-1]+1})" for g in groups) or "无"


lines = ["# 任务 C 数据对照", "", "由 `runs/c-preparation/summarize.py` 从各轮原始文件生成。错误时段按计划发送秒归桶，区间左闭右开；p99 仅含成功请求。", "", "| 实验 | 发送 | 成功 | 全程错误 | HTTP 错误码 | 超时 | p99 ms | 有错误的秒数 | 错误时段 s | loadgen CPU % | 发送滞后 p99 ms |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for name in names:
    run = root / name
    step = rows(run / "steps.csv")[0]
    timeline = rows(run / "timeline.csv")
    bad = [int(x["sec"]) for x in timeline if int(x["errors"]) > 0]
    errors = sum(int(x["errors"]) for x in timeline)
    assert errors == sum(int(step[k]) for k in ("http_err", "timeout", "net_err", "dropped"))
    lines.append(f'| {name} | {step["sent"]} | {step["ok"]} | {errors} | {step["codes"] or "无"} | {step["timeout"]} | {step["p99_ms"]} | {len(bad)} | {intervals(bad)} | {step["gen_cpu_pct"]} | {step["lag_p99_ms"]} |')

lines += ["", "## C3 按实例对照", "", "来源：各轮 `prometheus-range.json`。下表是 30 秒滚动指标在第 90～175 秒（降额稳定期，5 秒一个采样点）的 CPU/节流比例中位数，以及滚动 p99 的最大值；后者不是这一阶段全部请求的 p99。", "", "| 实验 | 实例 | CPU 核数中位数 | 配额核数中位数 | 节流比例中位数 | 最大滚动 p99 ms | down 次数 | ejected 次数 |", "|---|---|---|---|---|---|---|---|"]
for name in names[-2:]:
    run = root / name
    start = float(rows(run / "steps.csv")[0]["start_unix"])
    data = json.loads((run / "prometheus-range.json").read_text(encoding="utf-8"))
    events = [e for e in rows(run / "lbd-events.csv") if start <= int(e["unix_ms"])/1000 < start+240]
    for port in (8101, 8102, 8103):
        addr = f"127.0.0.1:{port}"

        def values(key):
            result = []
            for series in data[key]["response"]["data"]["result"]:
                metric = series["metric"]
                if metric.get("backend", metric.get("instance")) == addr:
                    result += [float(v) for t, v in series["values"] if 90 <= t-start <= 175 and math.isfinite(float(v))]
            return result

        cpu = statistics.median(values("cpu_cores"))
        quota = statistics.median(values("quota_cores"))
        throttle = statistics.median(values("throttle_ratio"))
        p99 = max(values("backend_p99_seconds"))*1000
        counts = [sum(e["backend"] == addr and e["event"] == kind for e in events) for kind in ("down", "ejected")]
        lines.append(f"| {name} | {port} | {cpu:.6f} | {quota:.2f} | {throttle:.4f} | {p99:.2f} | {counts[0]} | {counts[1]} |")
(root / "c-preparation" / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
