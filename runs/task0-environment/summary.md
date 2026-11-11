# Task 0 environment

## Project

Group: 8
Repository: https://github.com/aCannedFish/ops-lab3-8

Captured on host: ecs-249f

## Cloud instance

Huawei Cloud ECS
instance_type=x1e.2u.4g
resource_spec=x1e.2u.4g.linux
region=cn-east-3
availability_zone=cn-east-3a

## CPU

CPU(s):                                  2
Model name:                              General Purpose Processor

## Memory and swap

               total        used        free      shared  buff/cache   available
Mem:            3531        1158         411         410        2661        2373
Swap:              0           0           0

swapon --show output:

(empty: no swap device)

## Operating system

PRETTY_NAME="Ubuntu 24.04.5 LTS"
6.8.0-146-generic
systemd 255 (255.4-1ubuntu8.17)

## cgroup v2

cgroup2fs
cpuset cpu io memory hugetlb pids rdma misc

## CPU affinity plan

Instance processes: CPU 1
loadgen, lbd, scaler, Prometheus, node_exporter: CPU 0
Host CPU count: 2

## Tool versions

go version go1.26.9 linux/amd64
prometheus, version 3.13.4 (branch: HEAD, revision: 007a9e9ba628f815ce83e1ba9f29b97981996c3c)
node_exporter, version 1.12.1 (branch: HEAD, revision: 6044da783597cc3b57aef7580ddcdcff58a4ee99)

## Prometheus targets

{
    "status": "success",
    "data": {
        "activeTargets": [
            {
                "discoveredLabels": {
                    "__address__": "127.0.0.1:8081",
                    "__always_scrape_classic_histograms__": "false",
                    "__convert_classic_histograms_to_nhcb__": "false",
                    "__metrics_path__": "/metrics",
                    "__scheme__": "http",
                    "__scrape_interval__": "1s",
                    "__scrape_native_histograms__": "false",
                    "__scrape_timeout__": "1s",
                    "job": "enrolld"
                },
                "labels": {
                    "instance": "127.0.0.1:8081",
                    "job": "enrolld"
                },
                "scrapePool": "enrolld",
                "scrapeUrl": "http://127.0.0.1:8081/metrics",
                "globalUrl": "http://ecs-249f:8081/metrics",
                "lastError": "Get \"http://127.0.0.1:8081/metrics\": dial tcp 127.0.0.1:8081: connect: connection refused",
                "lastScrape": "2026-11-11T11:13:47.719566635+08:00",
                "lastScrapeDuration": 0.00027367,
                "health": "down",
                "scrapeInterval": "1s",
                "scrapeTimeout": "1s"
            },
            {
                "discoveredLabels": {
                    "__address__": "127.0.0.1:8090",
                    "__always_scrape_classic_histograms__": "false",
                    "__convert_classic_histograms_to_nhcb__": "false",
                    "__metrics_path__": "/metrics",
                    "__scheme__": "http",
                    "__scrape_interval__": "1s",
                    "__scrape_native_histograms__": "false",
                    "__scrape_timeout__": "1s",
                    "job": "lbd"
                },
                "labels": {
                    "instance": "127.0.0.1:8090",
                    "job": "lbd"
                },
                "scrapePool": "lbd",
                "scrapeUrl": "http://127.0.0.1:8090/metrics",
                "globalUrl": "http://ecs-249f:8090/metrics",
                "lastError": "Get \"http://127.0.0.1:8090/metrics\": dial tcp 127.0.0.1:8090: connect: connection refused",
                "lastScrape": "2026-11-11T11:13:48.424249537+08:00",
                "lastScrapeDuration": 0.000304401,
                "health": "down",
                "scrapeInterval": "1s",
                "scrapeTimeout": "1s"
            },
            {
                "discoveredLabels": {
                    "__address__": "127.0.0.1:9100",
                    "__always_scrape_classic_histograms__": "false",
                    "__convert_classic_histograms_to_nhcb__": "false",
                    "__metrics_path__": "/metrics",
                    "__scheme__": "http",
                    "__scrape_interval__": "5s",
                    "__scrape_native_histograms__": "false",
                    "__scrape_timeout__": "5s",
                    "job": "node"
                },
                "labels": {
                    "instance": "127.0.0.1:9100",
                    "job": "node"
                },
                "scrapePool": "node",
                "scrapeUrl": "http://127.0.0.1:9100/metrics",
                "globalUrl": "http://ecs-249f:9100/metrics",
                "lastError": "",
                "lastScrape": "2026-11-11T11:13:43.830917801+08:00",
                "lastScrapeDuration": 0.015129854,
                "health": "up",
                "scrapeInterval": "5s",
                "scrapeTimeout": "5s"
            }
        ],
        "droppedTargets": [],
        "droppedTargetCounts": {
            "enrolld": 0,
            "instances": 0,
            "lbd": 0,
            "node": 0
        }
    }
}
