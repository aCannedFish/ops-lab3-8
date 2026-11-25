# 任务 C 执行记录

本轮只完成任务 C（C1、C2 两组、C3 两组），不推进 D、E 或选做。详细数据和结论填写在 `LAB3.md` 第 4 节。

## 环境与源码

- 日期：2026-11-25；使用本机 SSH 配置中的 `se-devops`。
- 将本地源码打包传到服务器 `/home/ubuntu/lab3c-run`，在该目录 `make build test`；日志为 `build-test.log`。服务器未执行 Git 拉取、提交或推送。
- 源码基准为 `source-commit.txt` 中的本地提交。独立实验目录不含 `.git`，所以 `run3.sh` 的 `meta.txt` 把仓库提交记为“无”；以该基准和本次本地 diff 核对源码。
- lbd 和 scaler 分别运行在 `lab3-c-lbd.service`、`lab3-c-scaler.service`，绑定 CPU 0。scaler 为 `-mode fixed -replicas 3`，其余参数默认；实例 CPU 1、CPUQuota=25%、MemoryMax=128M、MemorySwapMax=0、`-warmup 60s -work 1000000`。每轮详细配置保存在 `meta.txt`。
- 复用原有 CPU 0 上的 Prometheus 和 node_exporter。将旧 `/home/ubuntu/lab3/data/targets.json` 保存为同目录 `targets-before-c.json`，原路径临时链接到本轮 `data/targets.json`。
- 启动检查发现 Prometheus 内存中的旧配置仍引用 `data/targets.json`，而磁盘配置已为 `../data/targets.json`；向原 Prometheus 发送 SIGHUP 重新加载后，实例指标恢复采集。C1 第 55 秒的 30 秒用量窗口已有完整采样。实际监控配置见 `prometheus-config.json`，初始目标状态见 `prometheus-targets-start.json`。

## 执行顺序

在实验目录建立上述两个 systemd 服务后，用 `run-case.sh` 依次执行：

```bash
bash runs/c-preparation/run-case.sh c1-stop
python3 runs/c-preparation/collect-prometheus.py c1-stop
python3 runs/c-preparation/predict-c3.py
bash runs/c-preparation/run-case.sh c2-default
python3 runs/c-preparation/collect-prometheus.py c2-default
bash runs/c-preparation/run-case.sh c2-sensitive
python3 runs/c-preparation/collect-prometheus.py c2-sensitive
bash runs/c-preparation/run-case.sh c3-slow 13
python3 runs/c-preparation/collect-prometheus.py c3-slow
bash runs/c-preparation/run-case.sh c3-outlier 13
python3 runs/c-preparation/collect-prometheus.py c3-outlier
python3 runs/c-preparation/summarize.py
```

脚本每轮重启 lbd、等待 3 台健康，调用原有 `scripts/run3.sh`，并按负载时刻调用 `scripts/inject.sh`。C1 第 60 秒 kill 8102、第 160 秒暂停 8103 共 20 秒；C2 第 40 秒暂停全部实例 2 秒；C3 第 60 秒将 8101 降至 13%，第 180 秒恢复 25%。C3 选 8101 是为了使用 C1 中同一存活实例的基线用量。scaler 补建复用了 8102 端口。

## C1 命令返回异常

首次 `systemctl kill --signal=SIGKILL` 已杀死 8102，systemd 记录主进程退出状态 9，scaler 随即移除并补建；但 systemctl 随后报 `Failed to send signal SIGKILL to auxiliary processes: Invalid argument`，使定时脚本提前返回。后台的 run3/loadgen 持续运行，另一个后台命令仍严格在原负载第 160 秒注入 pause，第 180 秒恢复，记录见 `c1-pause.log`、`c1-stop/marks.csv` 和 `instances.csv`。未重启负载，也未改写原始输出。

将 `scripts/inject.sh` 的 kill 命令加上 `--kill-whom=main`，明确只向服务主进程发送 SIGKILL，避免辅助进程操作影响命令结果。这是本轮唯一的既有脚本修改。已用 `bash -n` 检查脚本语法，并在本机 systemd 上验证 main 选择器可用。

## 证据与口径

- 测前预测：`prediction.md` 和 `c3-prediction.md`；C3 配额依据：`c1-cpu-baseline.json`。
- 五轮目录中保留 run3 生成的 `meta.txt`、`steps.csv`、`timeline.csv`、`lbd-events.csv`、`instances.csv`、`decisions.csv`、`marks.csv`、`lbd-metrics-end.txt`、`loadgen.log`、`summary.md`。固定模式不运行反应式决策，因此 `decisions.csv` 只有表头是正常情况。
- 额外保存每轮 `prometheus-range.json`，内含查询、时间范围和原始响应，供按实例核对 CPU、配额、节流、延迟与健康状态。
- `comparison.md` 是由 `summarize.py` 读取上述文件生成的对照表，不修改原始数据。
- `lab3sum` 在没有判定事件时，“注入到判定之间的错误”实际统计注入后的约 30 秒；有判定时使用整秒桶近似，可能漏掉边界错误。恢复用时从注入算起；C3 的 restored 表示摘除到期，不表示 CPU 配额已恢复。全程 p99 仅统计成功请求。
- 客户端精确样本 p99 与 Prometheus 直方图的 30 秒滚动估计口径不同；不能平均各实例 p99 当成全站 p99。

## 完成状态

五轮原始数据均已同步回本地仓库。C1 错误 161 个；C2 宽松/灵敏组错误 28/388 个；C3 不摘除/离群摘除组均无错误，成功请求 p99 为 37.22/14.84ms。数值见 `comparison.md` 及对应原始文件。

最后一轮第 180 秒已恢复 25% 配额。随后停止本轮 lbd、scaler 及其全部实例，`systemctl list-units --all 'lab3-*'` 为 0 个单元；原监控目标文件已恢复，Prometheus 仍正常运行。未删除 bin、tools、data 或任何实验数据，清理记录为 `cleanup.txt`。未执行 push。
