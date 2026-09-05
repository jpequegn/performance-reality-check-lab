# Example: measurements and compiler evidence

This is one local observation, not a universal language ranking. The complete
generated bundles remain local under `reports/`; binaries and raw benchmark
artifacts are not committed. Generate your own bundle to inspect its provenance.

## Setup and quality gates

- Apple M4, macOS Darwin 25.5.0, arm64.
- CPython 3.12.12; Rust 1.92.0, LLVM 21.1.3.
- Size 4096, seed 7; all four workloads and three variants in both languages.
- Default compiler flags recorded by the evidence manifest.

The first run used seven samples and 20 ms batches. It exited with code 2 and
preserved an invalid report: Python's allocating chase had a coefficient of
variation around 22.6%, above the 20% limit. That run is not a regression baseline.

The second run used longer batches without relaxing the quality threshold:

```sh
uv run reality-check run --out reports/longer-batches --min-ms 50 --samples 9
uv run reality-check inspect reports/longer-batches
```

All 24 rows passed. The largest coefficient of variation was approximately 7.96%.
Inspection verified the saved evidence. Comparing the report with itself also
passed as a CLI smoke test; that is not evidence of a real before/after speedup.

## Selected medians

Times below are microseconds per invocation, rounded from saved measurements.

| Workload | Language | Loop | Unrolled | Allocating |
| --- | --- | ---: | ---: | ---: |
| reduction | Python | 45.204 | 81.610 | 52.553 |
| reduction | Rust | 0.498 | 0.391 | 0.832 |
| chase | Python | 81.497 | 65.604 | 88.098 |
| chase | Rust | 4.068 | 4.115 | 4.623 |
| strided | Python | 136.045 | 137.949 | 141.649 |
| strided | Rust | 0.760 | 0.553 | 1.044 |
| branch | Python | 110.453 | 169.583 | 121.212 |
| branch | Rust | 0.886 | 0.791 | 1.269 |

Unrolling did not help Python's ordinary reduction in this run. Rust's unrolled
reduction was faster than its ordinary loop, but the chase results did not show
that pattern. These observations warrant inspection, not a blanket optimization
rule. Timing includes the harness overhead described in the methodology.

Each Rust allocating variant recorded one allocation of 32,768 bytes; ordinary
and unrolled variants recorded zero. Python reduction's traced peak was 112 bytes
for the loop and 32,880 for the allocating variant. The Python and Rust allocation
probes measure different quantities and should not be compared as equal metrics.

## What the generated assembly shows

The saved O3 ARM64 assembly contains vector loads and two-lane vector additions
inside `reduction_loop`:

```asm
LBB10_5:
    ldp q2, q3, [x12, #-16]
    subs x13, x13, #4
    add x12, x12, #32
    add.2d v0, v2, v0
    add.2d v1, v3, v1
    b.ne LBB10_5
```

The ordinary source loop was already vectorized. In contrast, `chase_loop` uses
the result of one indexed load to determine the next address:

```asm
LBB7_2:
    cmp x9, x1
    b.hs LBB7_6
    ldr x9, [x8, x9, lsl #3]
    subs x10, x10, #1
    add x0, x9, x0
    b.ne LBB7_2
```

These instructions support the distinction between independent arithmetic and a
dependent-load chain. They do not by themselves establish every cause of the
timing difference. Inspect your own function regions because compiler and target
changes can alter the instruction sequence and labels.

## The model needs review

All Rust rows exceeded the illustrative hardware-model throughput, while Python
rows did not. This flags the assumptions, not the measurements: the default
30 GB/s bandwidth and eight-cycle dependent-load assumptions are not calibrated
to this M4 or these warm working sets. Keep the measured results separate from
those assumptions and gather size-sweep evidence before revising the model.
