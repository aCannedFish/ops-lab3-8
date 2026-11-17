# A3 上限选取

200 MiB 基线在 20 请求/秒阶段开始后不久 OOM，标准 red.csv 在该阶段没有越过前 5 秒的样本。为取得目标到达率的 report_inflight_max，先把内存放宽到 512 MiB，运行相同随机种子的 10、20 请求/秒阶段，各 20 秒。

空载 RSS 为 8892416 / 1048576 = 8.48046875 MiB（a3-idle-metrics.txt）。定额计算将基线向上取为 16 MiB。改法一采用 (16 + report_inflight_max × 8 × 2) × 1.1，再向上取整到 16 MiB 的倍数。改法二使用 -report-max=11，因为 16 + 11×8×2 = 192 MiB < 200 MiB，下一档 12 将得到 208 MiB。两种改法都保持默认 GC，不设置 GOMEMLIMIT。
