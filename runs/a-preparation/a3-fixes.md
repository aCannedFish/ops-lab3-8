# A3 改法参数

以下参数在改法测量之前确定。

512 MiB 校准的目标 20 请求/秒阶段采到 report_inflight_max=17（runs/a3-size/red.csv 第 2 行，red-full.csv 同值）。RSS 峰值 314.375 MiB，cgroup 峰值采样 309.746 MiB。空载 RSS 8.48046875 MiB 向上按 16 MiB 计。

改法一：MemoryMax=(16+17×8×2)×1.1=316.8 MiB，向上取整到 320 MiB。保留 MemorySwapMax=0，不限并发，以相同 seed=1 连续运行 10、20、30 请求/秒，各 20 秒。320 MiB 按目标 20 请求/秒的有限窗口峰值估算，30 请求/秒用于观察进一步加压。

改法二：MemoryMax=200M，MemorySwapMax=0，report-max=11。算式为 16+11×8×2=192 MiB < 200 MiB；12 个并发得到 208 MiB。以相同的 10、20、30 请求/秒复测，预计并发超限返回 503，进程保持存活。
