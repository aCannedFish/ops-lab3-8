#!/usr/bin/env bash
# 在已有 Prometheus/node_exporter 的实验主机上运行 A3/O1；无需 root。
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p runs/o1-preparation
exec > >(tee -a runs/o1-preparation/execution.log) 2>&1
unit=lab3-a
cg=""
watcher=""
cleanup() {
  if [ -n "$watcher" ]; then kill "$watcher" 2>/dev/null || true; wait "$watcher" 2>/dev/null || true; fi
  systemctl --user stop "$unit" 2>/dev/null || true
}
trap cleanup EXIT
run_case() {
  local name=$1 memory=$2 limit=$3 cap=$4 rate=$5
  local dir=runs/$name
  [ ! -e "$dir" ] || { echo "Refusing to overwrite $dir"; exit 1; }
  systemctl --user stop "$unit" 2>/dev/null || true
  systemctl --user reset-failed "$unit" 2>/dev/null || true
  local start
  start=$(date -Iseconds)
  local env_args=(--setenv=GOGC=100)
  if [ -n "$limit" ]; then env_args+=(--setenv="GOMEMLIMIT=$limit"); fi
  systemd-run --user --unit="$unit" --property="MemoryMax=$memory" \
    --property=MemorySwapMax=0 --property=CPUQuota=100% --property=Restart=no \
    --property="WorkingDirectory=$PWD" "${env_args[@]}" \
    /usr/bin/taskset -c 1 "$PWD/bin/enrolld" -addr 127.0.0.1:8081 \
    -data "$PWD/data/$name" -report-max "$cap"
  local ready=0
  for ((i=0;i<50;i++)); do
    if curl -fsS http://127.0.0.1:8081/readyz >/dev/null 2>&1; then ready=1; break; fi
    sleep 0.1
  done
  [ "$ready" -eq 1 ] || { echo "Service did not become ready"; exit 1; }
  cg=$(systemctl --user show "$unit" -p ControlGroup --value)
  local audit
  audit=$(mktemp -d)
  systemctl --user show "$unit" -p ControlGroup -p MemoryMax -p MemorySwapMax \
    -p CPUQuotaPerSecUSec -p ExecStart -p Environment >"$audit/unit-start.txt"
  python3 -u - "$cg" >"$audit/cgroup-samples.csv" <<'PY' &
import csv, pathlib, sys, time
root = pathlib.Path('/sys/fs/cgroup' + sys.argv[1])
w = csv.writer(sys.stdout)
w.writerow(['unix_ms','memory_current','memory_peak','max_events','oom','oom_kill'])
while root.exists():
    try:
        ev = dict(line.split() for line in (root/'memory.events').read_text().splitlines())
        w.writerow([time.time_ns()//1000000, (root/'memory.current').read_text().strip(),
                    (root/'memory.peak').read_text().strip(),ev.get('max',0),ev.get('oom',0),ev.get('oom_kill',0)])
        sys.stdout.flush()
    except FileNotFoundError:
        break
    time.sleep(.1)
PY
  watcher=$!
  DATA="data/$name" SLO=1 GEN_CPUS=0 scripts/run.sh "$name" \
    -url 'http://127.0.0.1:8081/api/report?mb=8&ms=500' \
    -plan "0@10s,$rate@40s" -seed 1 -timeout 2s -stop-below 0 \
    -timeline "runs/$name/timeline.csv"
  kill "$watcher" 2>/dev/null || true
  wait "$watcher" 2>/dev/null || true
  watcher=""
  mv "$audit/"* "$dir/"
  rmdir "$audit"
  systemctl --user show "$unit" -p ActiveState -p Result -p ExecMainStatus \
    -p ExecMainCode -p NRestarts -p MemoryPeak -p MemorySwapPeak >"$dir/unit-end.txt"
  journalctl --user -u "$unit" --since "$start" --no-pager >"$dir/journal.txt"
  journalctl -k --since "$start" --no-pager >"$dir/kernel.txt" 2>"$dir/kernel-access.txt" || true
  cp deploy/queries-red.txt "$dir/queries-red.txt"
  cp deploy/queries-use.txt "$dir/queries-use.txt"
  scripts/table.sh "$dir" ok_rps error_rate p99_ms inflight_avg report_inflight_max \
    rss_max_mb heap_max_mb mem_current_max_mb mem_limit_mb gc_per_s cpu_ms_per_req >"$dir/table.md"
  echo "=== Completed $name ==="
  cat "$dir/unit-end.txt"
}
for rate in 10 20 30; do run_case "a3-default-$rate" 200M '' 0 "$rate"; done
for rate in 10 20 30; do run_case "o1-limit160-$rate" 200M 160MiB 0 "$rate"; done
run_case o1-limit160-overload 200M 160MiB 0 60
date -Iseconds >runs/o1-preparation/completed.txt
