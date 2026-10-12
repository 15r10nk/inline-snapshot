"""A/A control: identical code under two labels, measured in ABBA order."""
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from asv_runner.benchmarks.timeraw import _SeparateProcessTimer
from benchmarks.bench_snapshot import Comparison

root = Path('aa-results')
root.mkdir(exist_ok=True)
(root / 'metadata.json').write_text(json.dumps({
    'python': sys.version,
    'platform': platform.platform(),
    'affinity': sorted(os.sched_getaffinity(0)),
    'cpuinfo': Path('/proc/cpuinfo').read_text(),
    'sha': os.environ.get('GITHUB_SHA'),
    'method': 'Identical code, fresh subprocess per sample, number=1, blocks A B B A, 20 samples per block. No CPU affinity pinning.',
}, indent=2))
sample_count = int(os.environ.get('AA_SAMPLES', '20'))
rows = []
with (root / 'samples.jsonl').open('w') as output:
    for mode in ['plain', 'disabled']:
        full, setup = Comparison().timeraw_comparison('scalar', mode)
        assertions, checks = full.split('assert not state.missing_values', 1)
        for variant, statement in [('full', full), ('assertions', assertions), ('checks', 'assert not state.missing_values' + checks)]:
            timer = _SeparateProcessTimer(lambda: (statement, setup))
            for block, label in enumerate(['A', 'B', 'B', 'A']):
                values = []
                for sample in range(sample_count):
                    seconds = timer.timeit(1)
                    row = dict(mode=mode, variant=variant, block=block, label=label, sample=sample, seconds=seconds, timestamp=time.time())
                    rows.append(row)
                    output.write(json.dumps(row) + '\n')
                    output.flush()
                    values.append(seconds)
                print(mode, variant, block, label, statistics.median(values) * 1e6, 'us', flush=True)
summary = []
for mode in ['plain', 'disabled']:
    for variant in ['full', 'assertions', 'checks']:
        a, b = [statistics.median(r['seconds'] for r in rows if r['mode'] == mode and r['variant'] == variant and r['label'] == label) for label in ['A', 'B']]
        summary.append(dict(mode=mode, variant=variant, a_us=a*1e6, b_us=b*1e6, change_percent=(b/a-1)*100))
(root / 'summary.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
