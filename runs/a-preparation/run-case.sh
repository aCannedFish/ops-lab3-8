#!/usr/bin/env bash
# 采集任务 A 的 systemd/cgroup 证据，并由普通用户运行仓库原有压测脚本。
set -euo pipefail
cd /home/ubuntu/lab3
name=${1:?需要实验名}
rates=${2:?需要到达率列表}
kind=${3:-cpu}
[ ! -e "runs/$name" ] || { echo "结果目录已存在：runs/$name"; exit 1; }
audit=$(mktemp -d)
start=$(date -Iseconds)
cg=$(systemctl show lab3-a -p ControlGroup --value)
systemctl show lab3-a -p ControlGroup -p CPUQuotaPerSecUSec -p CPUQuotaPeriodUSec -p MemoryMax -p MemorySwapMax -p Environment -p User -p ExecStart > "$audit/unit-start.txt"
curl -fsS http://127.0.0.1:8081/config > "$audit/config.json"
for file in cpu.max memory.max memory.swap.max; do
  printf '%s: ' "$file" >> "$audit/cgroup-start.txt"
  cat "/sys/fs/cgroup$cg/$file" >> "$audit/cgroup-start.txt"
done
# 每 50 ms 保留内存与 OOM 计数，补充每秒一次的 Prometheus 样本。
python3 -u - "$cg" > "$audit/cgroup-samples.csv" <<'PY' &
import csv
import pathlib
import sys
import time

root = pathlib.Path('/sys/fs/cgroup' + sys.argv[1])
writer = csv.writer(sys.stdout)
writer.writerow(['unix_ms', 'memory_current', 'memory_peak', 'max_events', 'oom', 'oom_kill'])
while root.exists():
    try:
        events = dict(line.split() for line in (root / 'memory.events').read_text().splitlines())
        writer.writerow([
            time.time_ns() // 1000000,
            (root / 'memory.current').read_text().strip(),
            (root / 'memory.peak').read_text().strip(),
            events.get('max', 0), events.get('oom', 0), events.get('oom_kill', 0),
        ])
        sys.stdout.flush()
    except FileNotFoundError:
        break
    time.sleep(0.05)
PY
watcher=$!
trap 'kill "$watcher" 2>/dev/null || true' EXIT
url=http://127.0.0.1:8081/api/courses/1
route='/api/courses/{id}'
slo=0.05
if [ "$kind" = memory ]; then
  url='http://127.0.0.1:8081/api/report?mb=8&ms=500'
  route=/api/report
  slo=1
fi
runuser -u ubuntu -- env GEN_CPUS=0 SLO="$slo" DATA=data/a-task scripts/run.sh "$name" \
  -url "$url" -rates "$rates" -step 20s -seed 1 -stop-below 0 \
  -timeline "runs/$name/timeline.csv" > "$audit/execution.log" 2>&1
kill "$watcher" 2>/dev/null || true
wait "$watcher" 2>/dev/null || true
trap - EXIT
systemctl show lab3-a -p ActiveState -p Result -p ExecMainStatus -p ExecMainCode -p NRestarts -p MemoryPeak > "$audit/unit-end.txt"
journalctl -u lab3-a --since "$start" --no-pager > "$audit/journal.txt"
journalctl -k --since "$start" --no-pager > "$audit/kernel.txt"
dmesg --time-format iso | grep -E 'oom-kill|Killed process|Out of memory' | tail -n 30 > "$audit/dmesg.txt" || true
mv "$audit/"* "runs/$name/"
rmdir "$audit"
cp deploy/queries-red.txt deploy/queries-use.txt "runs/$name/"
bin/promsteps -steps "runs/$name/steps.csv" -queries deploy/queries-red.txt -trim 0s \
  -var "route=$route" -var "slo=$slo" > "runs/$name/red-full.csv"
if [ "$kind" = memory ]; then
  scripts/table.sh "runs/$name" ok_rps error_rate p99_ms inflight_avg report_inflight_max rss_max_mb heap_max_mb mem_current_max_mb mem_limit_mb > "runs/$name/table.md"
else
  scripts/table.sh "runs/$name" ok_rps p50_ms p99_ms server_p99_ms gomaxprocs cg_limit_cores cg_cpu_cores throttle_ratio throttled_s_per_s > "runs/$name/table.md"
fi
chown -R ubuntu:ubuntu "runs/$name"
cat "runs/$name/table.md"
cat "runs/$name/unit-end.txt"
