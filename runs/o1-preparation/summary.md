# O1 GOMEMLIMIT：结果与交接

本轮只完成 O1 及它所需的 A3 默认 GC 基线，范围调整见 `scope.md`。A3 的提高内存上限、限制并发两种改法，以及其他必做、选做留给组员。仓库没有 Canvas 实验指导书；本文覆盖仓库中 O1 的主题，最终提交前应由组员核对指导书的具体检查点。

## 条件与复现

2026-11-13 在 `ssh se-devops` 的 `/home/ubuntu/lab3` 执行。Go 1.26.9；重新 `make build test` 全部通过，见 `build-test.log`。每组新建用户级 `lab3-a.service`，CPUQuota=100%、MemoryMax=200M（200 MiB）、MemorySwapMax=0、Restart=no；服务固定 CPU 1，loadgen 固定 CPU 0，监控进程也在 CPU 0。已读取存活探针的 `cpu.max`、`memory.max`、`memory.swap.max` 验证控制器实际生效；各组 `unit-start.txt` 和 `meta.txt` 保存正式运行配置。

固定 GOGC=100；对照组不设 GOMEMLIMIT，实验组设 GOMEMLIMIT=160MiB。接口 `/api/report?mb=8&ms=500`。每次先空载 10 秒，再以 Poisson 到达加压 40 秒，seed=1，timeout=2s，stop-below=0。每个对应速率的两组发出请求数完全相同，分别为 373、795、1202。负载阶段 p99 统计的是成功响应；服务死亡后的网络错误必须同时查看，不能用约 500 ms 的 p99 代表服务可用。

测量前预测在 `prediction.md`，保留未修改。复现命令：

```bash
ssh se-devops
cd /home/ubuntu/lab3
# 首次运行；脚本拒绝覆盖已存在的结果目录。
bash scripts/o1-report.sh
# 需 Prometheus 仍保留本轮数据；导出全部历史原始指标与汇总。
python3 scripts/o1-summarize.py
```

## 主要结果

所有数值来自 `comparison.csv`、各组 `steps.csv`、`gc.csv` 和 `cgroup-samples.csv`。

| 到达率 | 配置 | 成功/发送 | 错误率 | 成功响应 p99（ms） | cgroup 已采到的峰值（MiB） | 结果 |
|---|---|---|---|---|---|---|
| 10 | 默认 GC | 373/373 | 0% | 507.16 | 180.94 | 存活 |
| 10 | 160MiB | 373/373 | 0% | 507.23 | 156.95 | 存活 |
| 20 | 默认 GC | 10/795 | 98.74% | 511.26 | 200.00 | OOM |
| 20 | 160MiB | 795/795 | 0% | 507.13 | 181.06 | 存活 |
| 30 | 默认 GC | 5/1202 | 99.58% | 507.03 | 197.13 | OOM |
| 30 | 160MiB | 215/1202 | 82.11% | 510.23 | 196.72 | OOM |
| 60 | 160MiB | 0/2461 | 100% | 无成功请求 | 180.63 | OOM |

10 请求/秒时，设置软上限使 cgroup 峰值从 180.94 降至 156.95 MiB；RSS 的一秒采样峰值从 185.73 降至 161.801 MiB，p99 基本相同。GC 从 1.70588 次/秒变为 1.73529 次/秒，GC CPU 的估计值分别为 0.000672419、0.000628159 核。这一组不能证明设置软上限一定增加 GC CPU；差别很小且只有一次测量。

20 请求/秒时，设置软上限后 GC 为 4.76471 次/秒，GC CPU 约 0.0021557 核，占进程 CPU 的估计比例约 7.95%（`o1-limit160-20/gc.csv`）。该组在整个 40 秒负载阶段无错误，说明此次配置能改善这一负载下的内存生存情况。默认组在负载开始约 1 秒后即 OOM，没有足够存活样本作稳定 GC 成本对比，因此不能据此断言默认组和实验组的 GC CPU 差值。

30 请求/秒时，默认组负载开始约 1 秒后 OOM；160MiB 组约 9 秒后 OOM。后者成功数增加，但服务最终仍死亡。60 请求/秒时即使设置软上限也在首次成功响应前 OOM。不能把 160MiB 当作 RSS 硬上限或“不再 OOM”的保证。

## 解释与预测核对

请求把 8 MiB 缓冲保持约 500 ms，平均活跃报表数约为 λ×0.5，即 10/20/30 请求/秒时约 5/10/15 个，单是活跃报表对象分别约 40/80/120 MiB。Poisson 到达有突发，不存在仅凭平均到达率能确定的有限最大并发。基线、未回收对象、Go 运行时和 cgroup 中的其他内存会继续增加占用。默认 GOGC 按存活堆增长比例触发回收，不自动把 200 MiB cgroup 限制当作 Go 的堆目标；GOMEMLIMIT 能促使运行时更早回收和归还内存。

预测中的“10 存活、20 有风险、30 很可能 OOM”与本轮默认组相符。160MiB 对 20 请求/秒的改善得到验证，对 30 请求/秒未能避免 OOM。60 请求/秒平均活跃缓冲约 60×0.5×8=240 MiB，已大于 200 MiB cgroup 上限，GC 无法回收仍被请求引用的缓冲。因此软上限适用于有垃圾可回收、且存活对象能容纳的情况；活跃集本身太大时仍需限制并发或增大容量。

上述存活结论只覆盖此主机、此随机种子和 40 秒负载，不能外推为长时间或任意突发下的安全承诺。

## OOM 证据与采样限制

`a3-default-20/journal.txt` 的实际记录：

```text
Nov 13 22:13:52 ecs-249f systemd[3438346]: lab3-a.service: A process of this unit has been killed by the OOM killer.
Nov 13 22:13:52 ecs-249f systemd[3438346]: lab3-a.service: Main process exited, code=killed, status=9/KILL
Nov 13 22:13:52 ecs-249f systemd[3438346]: lab3-a.service: Failed with result 'oom-kill'.
```

同目录 `unit-end.txt`：ActiveState=failed、Result=oom-kill、ExecMainCode=2、ExecMainStatus=9、NRestarts=0。`cgroup-samples.csv` 在 unix_ms=1794579232274 读到 memory.peak=209715200、max=19、oom=1、oom_kill=1；与被杀证据一致。其余被杀组均有各自的 journal 和 unit-end 记录。

当前 ubuntu 用户不能免密 sudo，也不能读取内核 journal；`kernel-access.txt` 保存权限提示，`kernel.txt` 没有可见内核事件。若 A3 的评分严格要求 dmesg/kern.log 中的行，需由有权限的组员补取；本轮没有将其标为已获得。运行方式是 `systemd-run --user`，查询状态和日志也需要 `systemctl --user`、`journalctl --user`。

Prometheus 每秒抓取；标准 `red.csv` 还按默认设置丢弃每阶段开头 5 秒，故启动负载后迅速 OOM 的组可能完全没有负载指标。额外导出 `red-full.csv`（trim=0）和 `prometheus-range.json` 保留整个阶段的可用样本，但它们也可能漏掉死亡前的峰值。`inflight_avg` 在死亡组中只代表可见样本，不能解释为全阶段平均并发。

cgroup 每 100 ms 采样，某些 OOM 时 cgroup 在下一个采样前已经销毁，因而采到的峰值可能小于 200 MiB，且 oom_kill_sampled=0；这不反驳 systemd 已记录的 OOM。`unit-end.txt` 中 systemd 的 MemoryPeak 也可能因 cgroup 已销毁而仅保留很小的末尾值，分析采用 `cgroup-samples.csv` 中已观察到的最高 memory.peak，并明确其为下界。进程 RSS 与 cgroup 内存的记账对象和共享页归属不同，也不应要求两者数值严格相等。

死亡后的 `rate()` 可能按剩余样本外推，不能用被杀组的 gc_per_s 或 gc_cpu_cores 作为正常持续运行时的成本。核心结论以成功数、OOM 日志和存活组的测量为依据。

## 文件与交接

每组保存 `meta.txt`、`steps.csv`、`timeline.csv`、`red.csv`、`red-full.csv`、`gc.csv`、`use.csv`、`prometheus-range.json`、开始/结束指标、sysstat 原始日志、cgroup 采样、unit 配置与状态、journal、查询快照。死亡组取不到 metrics-end 属于预期现象。总表为 `comparison.csv` / `comparison.md`。

本轮补全 `deploy/queries-red.txt` 的 throttle_ratio，新增 O1 GC 查询、运行脚本、历史查询与汇总脚本。未修改 Go 程序。实验运行进程已退出，被测服务已停止，9090/9100 的原有监控进程继续运行。所有结果已同步回本地仓库；不提交或推送，供合作者审阅。
