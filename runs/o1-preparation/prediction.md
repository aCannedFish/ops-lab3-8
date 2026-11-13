# A3 与 O1：测量前预测

记录时间：2026-11-13，所有本轮报表负载测量之前写入；此文件在测量后不修改。

## 环境与方案

目标主机 se-devops（ecs-249f）。使用用户级 systemd 独立 cgroup，因为 SSH 用户不能免密 sudo。已用存活探针读取 cgroup 文件，验证 MemoryMax=200M、MemorySwapMax=0、CPUQuota=100% 实际生效。服务用 taskset 固定 CPU 1；loadgen 用 CPU 0。Prometheus 对单实例每秒抓取一次。保持 GOGC=100、随机种子 1、Poisson 到达、单次请求超时 2 秒，各负载阶段 40 秒，开始前有 10 秒空载阶段；每次实验重新启动服务。接口为 /api/report?mb=8&ms=500。

实验组：

- a3-default-10/20/30：MemoryMax=200M，不设 GOMEMLIMIT、不限制报表并发。
- o1-limit160-10/20/30：MemoryMax=200M、GOMEMLIMIT=160MiB、不限制报表并发。
- a3-memory320-30：MemoryMax=320M，不设 GOMEMLIMIT、不限制并发。
- a3-concurrency12-30：MemoryMax=200M，不设 GOMEMLIMIT，-report-max=12。
- o1-limit160-overload：MemoryMax=200M、GOMEMLIMIT=160MiB，60 请求/秒，检验软上限无法回收仍在使用的对象。

## A3 预测

按 Little 定律，忽略分配与调度时间，10、20、30 请求/秒的平均在途数约为 5、10、15，活跃报表对象分别占 40、80、120 MiB。Poisson 到达没有有限的确定性最大在途数；40 秒测量中粗略预计峰值约为 12、20、27，对应活跃报表约 96、160、216 MiB，需用实测检查。进程基线、Go 运行时、尚未回收的对象及页缓存还会增加 RSS/cgroup 占用。默认 GOGC=100 的堆目标可能接近存活对象的两倍，因此预测 10 请求/秒可存活、20 请求/秒有 OOM 风险、30 请求/秒很可能 OOM；不能把这些概率预测当作已测结论。

提高上限采用 320 MiB：以预计峰值 27 × 8 = 216 MiB 活跃对象，加暂估 16 MiB 基线和 88 MiB GC/缓存余量。此为当前有限时长负载的试验值，不构成 Poisson 流量的严格最坏情况保证。限制并发 12 时，活跃报表上界为 96 MiB，200 MiB 余量约 104 MiB 供基线与 GC 使用；预计能避免 OOM，但 30 请求/秒下会出现主动 503。

## O1 预测

160 MiB 是 200 MiB cgroup 上限的 80%，为运行时外的内存及瞬时分配留出约 40 MiB。预计它能缩短垃圾滞留、提高 GC 频率，让 20 请求/秒更稳定，并可能改善 30 请求/秒的生存情况。代价是 GC CPU 成本上升，延迟可能增加。GOMEMLIMIT 是 Go 运行时软上限，并非 RSS/cgroup 硬限额，不保证不 OOM。

60 请求/秒平均约 30 个活跃报表，仅活跃对象就约 240 MiB，大于 cgroup 的 200 MiB。预计即使设置 GOMEMLIMIT=160MiB 仍会 OOM；此时必须限制并发或提供足够内存。
