# 实验 3 记录：第 <组号> 组

评分时依据本文件和 `runs/` 中的原始数据核对。本文件中的每一个数值，都须能在某个 `runs/<名字>/` 的文件中找到：表格用 `scripts/table.sh` 生成或从 `summary.md` 中复制后粘贴，其他数值注明出处（例如“`runs/b2-cpu/summary.md` 缺口表第 1 行”）。不要只贴截图。将 `<填写>` 替换为本组的内容。

标有“预测”的小节须在对应的测量之前写好，写好后不要修改。预测错误不扣分，与实测不一致之处在分析中讨论。

## 1. 基本信息

| 项 | 内容 |
|---|---|
| 小组 | 第 8 组（`runs/task0-environment/summary.md`） |
| 仓库地址 | <https://github.com/aCannedFish/ops-lab3-8> |
| 主机 | 华为云 ECS `x1e.2u.4g`（`runs/task0-environment/summary.md`） |
| CPU | `General Purpose Processor`；2 vCPU（`runs/task0-environment/summary.md`） |
| 内存与 swap | `free -m` total：3531 MiB；无 swap（`runs/task0-environment/summary.md`） |
| 操作系统、内核、systemd | Ubuntu 24.04.5 LTS；`6.8.0-146-generic`；systemd 255（255.4-1ubuntu8.17）（`runs/task0-environment/summary.md`） |
| cgroup | `cgroup2fs`；`cpuset cpu io memory hugetlb pids rdma misc`（`runs/task0-environment/summary.md`） |
| Go、Prometheus、node_exporter | Go 1.26.9；Prometheus 3.13.4；node_exporter 1.12.1（`runs/task0-environment/summary.md`） |
| 分核 | 后续实例：CPU 1；loadgen、lbd、scaler、Prometheus、node_exporter：CPU 0（`runs/task0-environment/summary.md`） |

## 2. 任务 A：配额，节流与 OOM

### 2.1 A1 配额算术

预测（测量之前写）：配额 0.5 核、周期 100 ms 时，1 个和 2 个线程跑满，每个线程每个周期运行多久、被停多久？本机上 enrolld 的 GOMAXPROCS 会是几，为什么？配额预算为每 100 ms 共 50 ms CPU 时间。1 个忙线程预计运行 50 ms、被停 50 ms；2 个线程分别在两个核上同时忙时，每个预计运行 25 ms、被停 75 ms。本机有 2 个 vCPU，未设置 GOMAXPROCS，预计 Go 1.26.9 的 GOMAXPROCS 为 2。 预测原文见 `runs/a-preparation/predictions.md`。

两次 `-burn` 的输出（`runs/a1-burn/burn-1.txt`、`burn-2.txt`）：

```text
cgroup：/sys/fs/cgroup/system.slice/run-r260b04c6c7ad4b16a9a05c4f106e07c1.scope
cpu.max：配额 0.50 核，周期 100ms（每个周期最多 50 ms CPU 时间）
GOMAXPROCS=2，忙线程 1 个，计数 10.0 秒
实际用核 0.50；周期 100 个，被节流 100 个（100%）；被停共 5.05 秒（按 CPU 累计）
每个线程每个周期被停：实测 50.5 ms，算术 50.0 ms
cgroup：/sys/fs/cgroup/system.slice/run-rbcbdf7b9955c42508481df1fec762389.scope
cpu.max：配额 0.50 核，周期 100ms（每个周期最多 50 ms CPU 时间）
GOMAXPROCS=2，忙线程 2 个，计数 10.0 秒
实际用核 0.50；周期 100 个，被节流 100 个（100%）；被停共 14.89 秒（按 CPU 累计）
每个线程每个周期被停：实测 74.4 ms，算术 75.0 ms
```

| 线程数 | 周期数 | 被节流的周期 | 实际用核 | 每线程每周期被停（实测） | 算术 |
|---|---|---|---|---|---|
| 1 | 100 | 100 | 0.50 核 | 50.5 ms | 运行 50 ms、被停 50 ms |
| 2 | 100 | 100 | 0.50 核 | 74.4 ms | 每线程运行 25 ms、被停 75 ms |

两次 GOMAXPROCS 均为 2。本机有两个可用逻辑核，Go 1.26.9 在这个条件下默认至少使用 2 个 P，因此 0.5 核配额下仍能同时运行两个 Go 线程。CPU 配额约束的是每个周期累计消耗的 CPU 时间。

### 2.2 A2 节流与 p99

本组写的节流比例查询（与 `deploy/queries-red.txt` 一致）：

```text
throttle_ratio      rate(cgroup_cpu_throttled_periods_total{job="enrolld"}[${window}]) / rate(cgroup_cpu_periods_total{job="enrolld"}[${window}])
```

配额 100% 时测得的每请求 CPU：4.26579 ms（`runs/a2-base/red.csv` 第 2 阶段的 `cpu_ms_per_req`）；据此选定到达率 94 请求/秒，预计平均约 0.400984 核。计算记录见 `runs/a-preparation/prediction-a2.md`。

预测（配额改为 50% 之前写）：平均用量低于配额，p99 会不会变？节流比例大约多少？100% 配额基线的 60 请求/秒阶段测得每请求 CPU 为 4.26579 ms，据此 R=round(400/4.26579)=94 请求/秒，预计平均用量 94×4.26579/1000=0.400984 核。50% 配额下，Poisson 突发和两个线程并行可能提前耗尽周期预算，预计 p99 从约十毫秒增加到数十毫秒，节流周期比例约 30%（估计范围 20%～40%）。 原文见 `runs/a-preparation/prediction-a2.md`。

各次实验的数据（`scripts/table.sh runs/<名字> ok_rps p50_ms p99_ms server_p99_ms gomaxprocs cg_limit_cores cg_cpu_cores throttle_ratio throttled_s_per_s`，每次一张表）：

100% 配额对照，来源：`runs/a2-q100/table.md`。

| step | target_rps | ok_rps | p50_ms | p99_ms | server_p99_ms | gomaxprocs | cg_limit_cores | cg_cpu_cores | throttle_ratio | throttled_s_per_s |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 94 | 96.7 | 6.95 | 16.57 | 16.0143 | 2 | 1 | 0.417873 | 0 | 0 |
| 2 | 94 | 91.2 | 6.94 | 11.28 | 9.98979 | 2 | 1 | 0.376712 | 0 | 0 |
| all | - | 93.9 | 6.95 | 13.50 | - | - | - | - | - | - |

50% 配额，来源：`runs/a2-q50/table.md`。

| step | target_rps | ok_rps | p50_ms | p99_ms | server_p99_ms | gomaxprocs | cg_limit_cores | cg_cpu_cores | throttle_ratio | throttled_s_per_s |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 94 | 96.7 | 6.98 | 41.75 | 40.3838 | 2 | 0.5 | 0.413295 | 0.335714 | 0.078296 |
| 2 | 94 | 91.2 | 6.98 | 46.20 | 42.4333 | 2 | 0.5 | 0.376231 | 0.192857 | 0.0575274 |
| all | - | 93.9 | 6.98 | 43.78 | - | - | - | - | - | - |

改法一，60% 配额，来源：`runs/a2-q60/table.md`。

| step | target_rps | ok_rps | p50_ms | p99_ms | server_p99_ms | gomaxprocs | cg_limit_cores | cg_cpu_cores | throttle_ratio | throttled_s_per_s |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 94 | 96.7 | 6.91 | 18.38 | 16.7533 | 2 | 0.6 | 0.413301 | 0.0642857 | 0.0106204 |
| 2 | 94 | 91.2 | 6.99 | 19.90 | 13.9842 | 2 | 0.6 | 0.372814 | 0.05 | 0.00401286 |
| all | - | 93.9 | 6.94 | 19.36 | - | - | - | - | - | - |

改法二，50% 配额、GOMAXPROCS=1，来源：`runs/a2-gmp1/table.md`。

| step | target_rps | ok_rps | p50_ms | p99_ms | server_p99_ms | gomaxprocs | cg_limit_cores | cg_cpu_cores | throttle_ratio | throttled_s_per_s |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 94 | 96.7 | 8.35 | 52.40 | 39.6826 | 1 | 0.5 | 0.408236 | 0.242857 | 0.042528 |
| 2 | 94 | 91.2 | 8.45 | 46.16 | 23.9 | 1 | 0.5 | 0.372851 | 0.142857 | 0.0202004 |
| all | - | 93.9 | 8.39 | 51.40 | - | - | - | - | - | - |

两种改法的测前参数依据见 `runs/a-preparation/a2-fixes.md`。60% 配额取自较高阶段用量 0.417873 / 0.7，再向上取整。GOMAXPROCS=1 的总体 p99 为 51.40 ms，高于原 50% 配额的 43.78 ms，本次没有改善尾延迟；该设置减少计算并行度，一个忙线程仍可用满一个核并耗尽 0.5 核预算。所有组请求均成功，loadgen CPU 约 2%，发送滞后 p99 约 1 ms。A2 按指导书允许服务使用 CPU 0、1，与绑定 CPU 0 的压测器和监控共享核。

### 2.3 A3 OOM

本节使用 2026-11-17 新测的系统级 `lab3-a.service`。已有 O1 默认 GC 基线保留在 `runs/a3-default-10`、`a3-default-20`、`a3-default-30`。本轮每次新建服务，以 10、20、30 请求/秒连续加压，各 20 秒，固定 seed=1、Poisson 到达、MemorySwapMax=0，不设置 GOMEMLIMIT。服务使用 CPU 0、1，loadgen 绑定 CPU 0。

预测（测量之前写）：`/api/report?mb=8&ms=500` 在到达率 10、20、30 时平均和最多各有几个在途请求？RSS 大约多少？在 `MemoryMax=200M` 下会在哪一个阶段被杀？本轮测前预测参考了 11 月 13 日已有的 O1 默认 GC 基线。按 λ×0.5 s，10、20、30 请求/秒的平均在途数为 5、10、15，活跃缓冲为 40、80、120 MiB；有限测量窗口中的峰值暂估 12、20、27，实际以采样为准。暂估基线 16 MiB，按 GOGC=100 的约两倍堆余量估算，平均内存规模约 96、176、256 MiB，突发时更高。预计 10 请求/秒存活，20 请求/秒首先发生 OOM，30 请求/秒也会超过 200 MiB。 预测原文见 `runs/a-preparation/predictions.md`。

200 MiB、不限报表并发，来源：`runs/a3-oom/table.md`。

| step | target_rps | ok_rps | error_rate | p99_ms | inflight_avg | report_inflight_max | rss_max_mb | heap_max_mb | mem_current_max_mb | mem_limit_mb |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 | 9.1 | 0.0000 | 506.85 | 4.2 | 7 | 137.312 | 105.37 | 132.355 | 200 |
| 2 | 20 | 1.9 | 0.9066 | 506.69 | - | - | - | - | - | - |
| 3 | 30 | 0.0 | 1.0000 | - | - | - | - | - | - | - |
| all | - | 3.6 | 0.8177 | 506.81 | - | - | - | - | - | - |

改法一，320 MiB、不限报表并发，来源：`runs/a3-limit320/table.md`。

| step | target_rps | ok_rps | error_rate | p99_ms | inflight_avg | report_inflight_max | rss_max_mb | heap_max_mb | mem_current_max_mb | mem_limit_mb |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 | 9.1 | 0.0000 | 507.51 | 4.8 | 8 | 137.68 | 121.388 | 132.984 | 320 |
| 2 | 20 | 19.8 | 0.0000 | 507.34 | 11.1333 | 18 | 314.191 | 185.497 | 309.57 | 320 |
| 3 | 30 | 0.3 | 0.9888 | 502.33 | - | - | - | - | - | - |
| all | - | 9.8 | 0.5129 | 507.34 | - | - | - | - | - | - |

改法二，200 MiB、报表并发上限 11，来源：`runs/a3-cap11/table.md`。

| step | target_rps | ok_rps | error_rate | p99_ms | inflight_avg | report_inflight_max | rss_max_mb | heap_max_mb | mem_current_max_mb | mem_limit_mb |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 | 9.1 | 0.0000 | 506.91 | 4.13333 | 7 | 136.668 | 105.361 | 131.676 | 200 |
| 2 | 20 | 16.4 | 0.1742 | 506.69 | 7.93333 | 11 | 185.996 | 169.411 | 181.113 | 200 |
| 3 | 30 | 19.5 | 0.3740 | 506.14 | 9.6 | 11 | 186.156 | 153.429 | 181.242 | 200 |
| all | - | 15.0 | 0.2515 | 506.69 | - | - | - | - | - | - |

被杀的证据（`systemctl show -p ActiveState,Result,ExecMainStatus lab3-a` 和 `journalctl -u lab3-a` 的相关行，`dmesg` 或 `/var/log/kern.log` 中的 oom-kill 行）：

```text
Result=oom-kill
ExecMainStatus=9
ActiveState=failed

Nov 17 19:01:43 ecs-249f systemd[1]: lab3-a.service: A process of this unit has been killed by the OOM killer.
Nov 17 19:01:43 ecs-249f systemd[1]: lab3-a.service: Main process exited, code=killed, status=9/KILL
Nov 17 19:01:43 ecs-249f systemd[1]: lab3-a.service: Failed with result 'oom-kill'.

Nov 17 19:01:43 ecs-249f kernel: oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=lab3-a.service,mems_allowed=0,oom_memcg=/system.slice/lab3-a.service,task_memcg=/system.slice/lab3-a.service,task=enrolld,pid=2398392,uid=1000
Nov 17 19:01:43 ecs-249f kernel: Memory cgroup out of memory: Killed process 2398392 (enrolld) total-vm:1528500kB, anon-rss:203812kB, file-rss:5888kB, shmem-rss:0kB, UID:1000 pgtables:508kB oom_score_adj:0
```

来源：`runs/a3-oom/unit-end.txt`、`journal.txt`、`kernel.txt`。20 请求/秒阶段发生 OOM，30 请求/秒阶段延续服务已停止的状态，全部请求失败。`-stop-below 0` 用于保留完整三个阶段。标准查询去掉阶段开头 5 秒，死亡阶段无样本的项保留为 `-`；完整窗口的残存样本另存于 `red-full.csv`。

两种改法：按目标 20 请求/秒的实测峰值估计，limit 取 320 MiB。校准组 `runs/a3-size/red.csv` 第 2 阶段的 `report_inflight_max=17`，空载 RSS 为 8.48046875 MiB，计算时向上按 16 MiB 计：`(16 + 17×8×2)×1.1 = 316.8 MiB`，再向上取为 320 MiB。限制并发时 `-report-max=11`，因为 `16 + 11×8×2 = 192 MiB < 200 MiB`，12 个并发则为 208 MiB。测前参数记录见 `runs/a-preparation/a3-calibration.md`、`a3-fixes.md`。

320 MiB 在目标 20 请求/秒时 396 个请求全部成功，30 请求/秒时再次 OOM。并发上限 11 的服务全程存活，20、30 请求/秒时分别成功 327/396、390/623，错误全部为主动 503（`runs/a3-cap11/steps.csv` 的 `codes`），错误率为 17.42%、37.40%。提高 limit 以更多内存承受负载；限制并发以拒绝超限请求保护进程。

本轮内核 OOM 证据已取得。50 ms 的 cgroup 采样在基线中记录到 197.2578125 MiB 峰值，尚未采到 oom_kill 增长时 cgroup 已被销毁，因此以 systemd 和内核日志确认被杀。基线采样与计算见 `runs/a-preparation/summary.md`。实验结束后已停止并清理 `lab3-a`，记录见 `runs/a-preparation/cleanup.txt`。

## 3. 任务 B：伸缩控制环

### 3.1 B0 单个实例的能力

<粘贴 `runs/b0-…/steps.csv` 的主要列，或 `scripts/table.sh runs/b0-… ok_rps p99_ms` 的输出>

单个实例（CPU 配额 <填写>%）的上限约 <填写> 请求/秒，按 0.7 的容量线可承担 <填写> 请求/秒；依据：<填写>。

本组的到达曲线：平时 <填写>、峰值 <填写> 请求/秒（`scripts/plan.sh` 的输出：`<填写>`）。

预测（B1～B3 之前写）：峰值需要几个实例？反应式从爬升开始到新实例就绪大约要多久，缺口大约多长？定时预热最晚何时开始？<填写>

### 3.2 三种方案的对照

| 方案 | `runs/` 目录 | 参数 | 缺口（秒） | 错误数 | 峰值阶段的 p99（ms） | 实例·分钟 |
|---|---|---|---|---|---|---|
| B1 常驻 | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> |
| B2 反应式（信号一） | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> |
| B2 反应式（信号二） | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> |
| B3 定时加反应式 | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> |

### 3.3 控制环各段的实测

以 B2（信号一）为例，从 `summary.md` 的“伸缩决策”和“实例”两张表读出：

| 段 | 起止 | 实测（秒） | L-11 第 10 页的设定 |
|---|---|---|---|
| 指标延迟与等待决策（爬升开始 → 第一次扩容决策） | <填写> | <填写> | 指标约 20 s + 决策 ≤ 15 s |
| 拉镜像（创建 → 启动） | <填写> | <填写> | 约 20 s |
| 启动、预热与健康检查（启动 → 就绪） | <填写> | <填写> | 约 60 s |
| 合计（爬升开始 → 新实例就绪） | <填写> | <填写> | 约 2 min |

B2 缺口中的错误：客户端超时 <填写> 个，lbd 返回的状态码 <填写>（`steps.csv` 的 `timeout`、`codes`）；这段时间 `lbd-events.csv` 中有 <填写> 次 `down`。

## 4. 任务 C：故障注入

| 注入 | `runs/` 目录 | lbd 的参数 | 判定用时（秒） | 恢复用时（秒） | 注入到判定之间的错误 | 全程错误 | 其他 |
|---|---|---|---|---|---|---|---|
| C1 停止（kill） | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> | 判定是 `removed` 还是 `down`：<填写>；补建的实例何时就绪：<填写> |
| C1 卡住（pause 一台 20 秒） | 同上 | 同上 | <填写> | <填写> | <填写> | 同上 | 判定是 `removed` 还是 `down`：<填写> |
| C2 暂停 2 秒（灵敏） | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> |
| C2 暂停 2 秒（宽松） | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> |
| C3 变慢（不摘除） | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> | 全站 p99：<填写> |
| C3 变慢（离群摘除） | <填写> | <填写> | <填写> | <填写> | <填写> | <填写> | 全站 p99：<填写> |

预测（C1 之前写）：按 lbd 的参数，一个实例停止或卡住以后多久被判定？其间大约有多少请求出错？<填写>

C1 中停止与卡住的判定用时各是多少，分别是谁发现的？与“间隔 × 失败阈值”相比如何？<填写>

C3 中把配额调到了多少，依据的用量 U 是多少：<填写>

C3 中健康检查为什么全部通过？用 `runs/<名字>/lbd-metrics-end.txt` 或 Prometheus 中按实例的数据，找出是哪一台变慢，并说明依据：<填写>

## 5. 任务 D：发布与自愈

### 5.1 D1 滚动发布

预测：按 L-05 第 24 页的公式，3 个实例逐个替换要多久？直接替换时大约多少请求出错？<填写>

| 做法 | `runs/` 目录 | 发布总时长（秒） | 错误数 | 出错的时段 | 说明 |
|---|---|---|---|---|---|
| 直接替换（naive） | <填写> | <填写> | <填写> | <填写> | <填写> |
| 排空加就绪（graceful） | <填写> | <填写> | <填写> | <填写> | <填写> |

### 5.2 D2 自愈

| 项 | 数值与出处 |
|---|---|
| 参数（`-restart`、`-args`、`-memory`） | <填写> |
| 每个实例的泄漏速度、预计多久 OOM 一次 | <填写> |
| 实测的重启次数（`systemctl show -p NRestarts lab3-inst-…`、`summary.md` 的“实例”表） | <填写> |
| 各实例重启的时刻（`instances.csv` 的 restarted 行）与缺口的时刻 | <填写> |
| 全程的成功率、错误数 | <填写> |

本组写的告警查询，以及它在这次实验中的值：

```text
<填写>
```

## 6. 分析问题

每题先列出所用数据（引用上面的表或 `runs/` 中的文件），再写结论，并说明结论的成立条件。每题 300～600 字。

**问题 1：配额。** A1 实测的每线程每周期被停时间与 L-09 第 12 页的算术相差多少，差异来自何处？A2 中平均用量低于配额时，p99 为什么变大？两种改法各改变了什么，各有什么代价？A3 中 RSS 的推算与实测是否一致？Go 的垃圾回收对“基线 + 在途数 × 每请求内存”这个估计有什么影响？`MemoryMax` 为什么要和 `MemorySwapMax=0` 一起设？按最坏情况定 limit 与限制并发，各适合什么条件？

<填写>

**问题 2：控制环。** 各段延迟的实测值是多少，哪一段最长，能压缩多少？三种方案的缺口与实例·分钟各是多少？两种信号的差别在哪里，为什么？B2 的缺口中除了超时，还有 lbd 返回的 503：过载为什么会让健康检查也失败，这使缺口变得更严重还是更轻？你们会为“开放日”选哪个方案，结论在什么条件下成立？（可选：思考题 3 第四幕中你们的判断，与这里测到的现象是否一致？）

<填写>

**问题 3：健康检查。** 停止、卡住、暂停、变慢四次注入中，各是谁、用多久发现的，健康检查看到了什么？检出快与误判少之间怎样取舍？离群摘除解决了什么问题，又带来什么风险？为什么要限制同时摘除的比例？

<填写>

**问题 4：发布与自愈。** 直接替换时，失败的请求来自哪几步？排空加就绪消除了哪几类失败，代价是什么？D2 中三个实例的重启时刻有什么关系，为什么？这对“有冗余，一台重启不影响服务”的假设意味着什么？自愈解决了什么、掩盖了什么？应当在哪一层、用什么指标告警？

<填写>

## 7. 选做记录

| 选做 | 完成情况与证据 |
|---|---|
| O1 GOMEMLIMIT | 已完成本轮对照与分析：测量前预测 `runs/o1-preparation/prediction.md`；证据及交接 `runs/o1-preparation/summary.md`；总表 `runs/o1-preparation/comparison.csv`。默认 GC 的 10/20/30 请求/秒基线在 `runs/a3-default-*`，GOMEMLIMIT=160MiB 的对应组及 60 请求/秒边界在 `runs/o1-limit160-*`。200MiB cgroup 下，20 请求/秒由默认组 OOM 改善为 795/795 成功，30 与 60 请求/秒仍 OOM，验证软上限无法约束过大的活跃集。使用已验证限额生效的用户级 systemd；内核日志权限限制见汇总。 |
| O2 两层伸缩 | <未做 / 参数、`runs/` 目录、结论> |
| O3 扩错层 | <未做 / 预测、`runs/` 目录、结论> |
| O4 Kubernetes 的 HPA | <未做 / 环境、配置文件、数据与结论> |
| O5 换负载均衡器 | <未做 / 配置文件、`runs/` 目录、结论> |
| O6 两台主机 | <未做 / 拓扑、`runs/` 目录、结论> |
| O7 迁移到小组项目 | <未做 / 仓库链接、做了什么、结论> |

## 8. 成员分工

每位成员一行，只填写 GitHub 用户名，无需填写姓名；行数应与小组人数一致。

| GitHub 用户名 | 负责的部分 |
|---|---|
| <用户名> | <填写> |
