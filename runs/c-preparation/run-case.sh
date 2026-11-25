#!/usr/bin/env bash
# 在实验目录运行；已有固定 3 实例 scaler 和 Prometheus。每轮重启 lbd，等全部健康。
set -euo pipefail
name=${1:?c1-stop|c2-default|c2-sensitive|c3-slow|c3-outlier}
quota=${2:-}
extra=()
case "$name" in
  c1-stop) duration=240 ;;
  c2-default) duration=120 ;;
  c2-sensitive) duration=120; extra=(-check-interval 500ms -check-timeout 200ms -fall 1) ;;
  c3-slow) duration=240; : "${quota:?需要 C1 用量计算出的配额}" ;;
  c3-outlier) duration=240; extra=(-outlier); : "${quota:?需要 C1 用量计算出的配额}" ;;
  *) exit 1 ;;
esac
sudo -n systemctl stop lab3-c-lbd
sudo -n systemd-run --unit=lab3-c-lbd --collect --uid=ubuntu \
  -p CPUAffinity=0 -p "WorkingDirectory=$PWD" \
  -p "StandardOutput=append:$PWD/runs/c-preparation/lbd.log" \
  "$PWD/bin/lbd" "${extra[@]}"
until curl -fsS http://127.0.0.1:8090/backends 2>/dev/null |
  python3 -c 'import json,sys; b=json.load(sys.stdin); sys.exit(not(len(b)==3 and all(x["up"] for x in b)))' 2>/dev/null; do
  sleep 1
done
rm -f data/run-start
scripts/run3.sh "$name" -url http://127.0.0.1:8080/api/courses/1 -plan "160@${duration}s" &
run_pid=$!
until [ -s data/run-start ]; do sleep 0.1; done
at() {
  python3 - "$1" <<'PY'
import pathlib,sys,time
start=int(pathlib.Path('data/run-start').read_text())
time.sleep(max(0,start+float(sys.argv[1])-time.time()))
PY
}
inject() {
  sudo -n systemd-run --quiet --wait --pipe --collect --unit=lab3-c-inject \
    -p "WorkingDirectory=$PWD" /bin/bash "$PWD/scripts/inject.sh" "$@"
}
case "$name" in
  c1-stop) at 60; inject kill 8102; at 160; inject pause 8103 20 ;;
  c2-*) at 40; inject pause all 2 ;;
  c3-*) at 60; inject slow 8101 "$quota"; at 180; inject restore 8101 25 ;;
esac
wait "$run_pid"
