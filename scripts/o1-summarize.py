#!/usr/bin/env python3
"""导出 A3/O1 的历史指标并生成汇总；在实验主机保留 Prometheus 数据时执行。"""
import csv
import json
import pathlib
import subprocess
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAMES = [f'a3-default-{r}' for r in (10, 20, 30)] + [
    f'o1-limit160-{r}' for r in (10, 20, 30)
] + ['o1-limit160-overload']
rows = []
for name in NAMES:
    directory = ROOT / 'runs' / name
    with (directory / 'steps.csv').open() as f:
        steps = list(csv.DictReader(f))
    load = next(s for s in steps if s['step'] == '2')
    (directory / 'queries-o1.txt').write_text((ROOT / 'deploy/queries-o1.txt').read_text())
    args = [str(ROOT / 'bin/promsteps'), '-steps', str(directory / 'steps.csv')]
    for output, query, trim in [('gc.csv', 'queries-o1.txt', '5s'),
                                ('red-full.csv', 'queries-red.txt', '0s')]:
        with (directory / output).open('w') as f:
            subprocess.run(args + ['-queries', str(ROOT / 'deploy' / query), '-trim', trim,
                                  '-var', 'route=/api/report', '-var', 'slo=1'],
                           stdout=f, check=True)
    params = urllib.parse.urlencode({
        'query': '{job="enrolld",__name__=~"process_resident_memory_bytes|go_heap_objects_bytes|http_inflight_requests|go_gc_cycles_total|go_gc_cpu_seconds_total|process_cpu_seconds_total|cgroup_memory_.*"}',
        'start': steps[0]['start_unix'], 'end': load['end_unix'], 'step': '1s',
    })
    with urllib.request.urlopen('http://127.0.0.1:9090/api/v1/query_range?' + params) as response:
        raw = json.load(response)
    if raw['status'] != 'success':
        raise RuntimeError(raw)
    (directory / 'prometheus-range.json').write_text(json.dumps(raw, indent=2) + '\n')
    with (directory / 'gc.csv').open() as f:
        gc = next(r for r in csv.DictReader(f) if r['step'] == '2')
    with (directory / 'red-full.csv').open() as f:
        red = next(r for r in csv.DictReader(f) if r['step'] == '2')
    with (directory / 'cgroup-samples.csv').open() as f:
        samples = list(csv.DictReader(f))
    state = dict(line.split('=', 1) for line in (directory / 'unit-end.txt').read_text().splitlines())
    peak = max(int(s['memory_peak']) for s in samples) / 1048576
    oom = max(int(s['oom_kill']) for s in samples)
    row = {'run': name, 'sent': load['sent'], 'ok': load['ok'],
           'http_err': load['http_err'], 'timeout': load['timeout'], 'net_err': load['net_err'],
           'ok_rps': load['ok_rps'], 'error_rate': load['error_rate'], 'p99_ms': load['p99_ms'],
           'cgroup_peak_mb': f'{peak:.2f}', 'oom_kill_sampled': oom, 'result': state['Result'],
           'rss_max_mb': red['rss_max_mb'], 'inflight_avg': red['inflight_avg'],
           'report_inflight_max': red['report_inflight_max'],
           'gc_per_s': gc['gc_per_s'], 'gc_cpu_cores': gc['gc_cpu_cores'],
           'process_cpu_cores': gc['process_cpu_cores'], 'gc_cpu_fraction': gc['gc_cpu_fraction']}
    rows.append(row)
with (ROOT / 'runs/o1-preparation/comparison.csv').open('w') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
columns = ['run', 'ok_rps', 'error_rate', 'p99_ms', 'rss_max_mb', 'cgroup_peak_mb',
           'result', 'gc_per_s', 'gc_cpu_cores']
lines = ['| ' + ' | '.join(columns) + ' |', '|' + '---|' * len(columns)]
lines += ['| ' + ' | '.join(str(r[c]) or '-' for c in columns) + ' |' for r in rows]
(ROOT / 'runs/o1-preparation/comparison.md').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
