# 任务 A 记录

实验日期：2026-11-17。实验主机：ecs-249f，目录 `/home/ubuntu/lab3`。本地记录基于 main 的 e808fcd，ECS 的 HEAD 为 4e453bc，Go 源码与本地相同；查询文件使用已完成的 throttle_ratio，各组保存了查询快照。

## 条件

使用系统级 `lab3-a.service`，配置 `User=ubuntu`，由 systemd 设置 cgroup 上限。这样普通用户运行的 scripts/run.sh 可以读取进程状态。首个启动检测因进程属主为 root 而失败，未施加负载，原始提示保存为 setup-firstattempt.txt。

A1 使用 systemd-run --scope、CPUQuota=50%，每种忙线程数持续 10 秒。A2 服务 work=2000000、MemoryMax=256M，允许 CPU 0、1，loadgen 绑定 CPU 0。A3 保留默认 work=200000、GOGC=100，不设置 GOMEMLIMIT，不设置 CPUQuota，MemorySwapMax=0。

所有 HTTP 负载使用 Poisson 到达、seed=1、step=20s、timeout=2s、stop-below=0。A2 SLO=0.05s，A3 SLO=1s。指标由已有 Prometheus 9090、node_exporter 9100 采集。run-case.sh 调用仓库 scripts/run.sh，并记录 systemd、kernel、cgroup；脚本由已认证的管理员 shell 执行，压测器以 ubuntu 运行。

## 预测

predictions.md 在本轮 A1、A3 测量前写入；prediction-a2.md 在改动到 50% 配额前写入；a2-fixes.md、a3-calibration.md、a3-fixes.md 记录各改法开始前确定的参数。这些预测文件保留原文。

## A2 汇总

| 运行 | 配额 | GOMAXPROCS | 到达率 | 总体 p99（ms） | 总体错误率 |
|---|---|---|---|---|---|
| a2-base | 1 核 | 2 | 30,60 | 11.01 | 0.0000 |
| a2-q100 | 1 核 | 2 | 94,94 | 13.50 | 0.0000 |
| a2-q50 | 0.5 核 | 2 | 94,94 | 43.78 | 0.0000 |
| a2-q60 | 0.6 核 | 2 | 94,94 | 19.36 | 0.0000 |
| a2-gmp1 | 0.5 核 | 1 | 94,94 | 51.40 | 0.0000 |

每请求 CPU 取 a2-base/red.csv 的第二阶段 4.26579 ms。R=round(400/4.26579)=94，预计 0.400984 核。提高配额的计算为 ceil(0.417873/0.7×100)=60%。

50% 配额的总体 p99 为 43.78 ms，100% 为 13.50 ms。60% 降到 19.36 ms。GOMAXPROCS=1 为 51.40 ms：节流比例下降，但本次客户端总体尾延迟没有改善。

## A3 汇总

| 运行 | 内存上限（MiB） | report-max | 阶段 | 成功/发送 | 错误率 | HTTP 状态码 |
|---|---|---|---|---|---|
| a3-oom | 200 | 0 | 10 req/s | 182/182 | 0.0000 | - |
| a3-oom | 200 | 0 | 20 req/s | 37/396 | 0.9066 | - |
| a3-oom | 200 | 0 | 30 req/s | 0/623 | 1.0000 | - |
| a3-size | 512 | 0 | 10 req/s | 182/182 | 0.0000 | - |
| a3-size | 512 | 0 | 20 req/s | 396/396 | 0.0000 | - |
| a3-limit320 | 320 | 0 | 10 req/s | 182/182 | 0.0000 | - |
| a3-limit320 | 320 | 0 | 20 req/s | 396/396 | 0.0000 | - |
| a3-limit320 | 320 | 0 | 30 req/s | 7/623 | 0.9888 | - |
| a3-cap11 | 200 | 11 | 10 req/s | 182/182 | 0.0000 | - |
| a3-cap11 | 200 | 11 | 20 req/s | 327/396 | 0.1742 | 503:69 |
| a3-cap11 | 200 | 11 | 30 req/s | 390/623 | 0.3740 | 503:233 |

200 MiB 基线在 20 请求/秒阶段 OOM，320 MiB 在 20 请求/秒存活、30 请求/秒 OOM。report-max=11 全程存活，在 20、30 请求/秒时主动返回 69、233 个 503。成功请求的 p99 约 0.5 秒，应与表中的失败数一起阅读。

## 内存计算

空载 RSS=8892416/1048576=8.48046875 MiB，取 16 MiB 作计算基线。512 MiB 校准在目标 20 请求/秒测得 report_inflight_max=17，RSS 采样峰值314.375 MiB、cgroup 采样峰值309.746 MiB。新上限=(16+17×8×2)×1.1=316.8 MiB，向上取320 MiB。并发上限11满足16+11×8×2=192 MiB<200 MiB；12对应208 MiB。

## 采样与清理

- a3-oom：50 ms 采样记录的 memory.peak 最大值为 197.2578125 MiB，采到的 oom_kill 最大值为 0。
- a3-size：50 ms 采样记录的 memory.peak 最大值为 309.99609375 MiB，采到的 oom_kill 最大值为 0。
- a3-limit320：50 ms 采样记录的 memory.peak 最大值为 317.84765625 MiB，采到的 oom_kill 最大值为 0。
- a3-cap11：50 ms 采样记录的 memory.peak 最大值为 181.63671875 MiB，采到的 oom_kill 最大值为 0。

死亡组的 cgroup 在最后一次采样后销毁，未采到 kill 计数增长。死亡组的 kernel.txt、journal.txt 和 unit-end.txt 提供实际 OOM 证据；unit-end 中销毁后的 MemoryPeak 不用于估计实验峰值。标准 red.csv 丢弃每阶段开头5秒，red-full.csv 保留完整窗口的可见样本。

已执行 systemctl stop lab3-a 和 systemctl reset-failed lab3-a，cleanup.txt 记录 LoadState=not-found、ActiveState=inactive。Prometheus 和 node_exporter 保持运行。
