# Capabilities, usage and learning

## What you can do

Run equivalent Python/Rust kernels and inspect the complete chain from source code
to machine code to measured behavior. The report keeps raw observations, allocation
evidence and theoretical assumptions separate. It also demonstrates a benchmark
rejecting its own results when sample quality is poor.

The repository provides a CLI and Markdown/JSON reports. It does not require a
GPU, model provider, network service or personal data. Dependencies are only needed
for installation and the local language toolchains.

## A useful first session

1. Install with `uv sync --locked` and run `uv run pytest`.
2. Run `uv run reality-check run --out reports/reduction --workload reduction`.
3. Read the three Python and three Rust rows. Check quality flags before comparing
   medians. Python unrolling may cost more interpreter work even when it exposes
   useful independence to a native compiler.
4. Follow the O3 assembly links for reduction_loop and reduction_unrolled. Find the
   loads and accumulator updates in each loop. Compare with O0 and LLVM IR.
5. Inspect the allocation section. The deliberate Rust copy should produce one
   allocation of 8*size bytes; the loop variant should produce none. Python's copy
   should increase traced peak memory.
6. Run the chase and strided workloads. Compare the dependent load sequence with
   independent reduction loads. Keep the observed cause tentative until the
   assembly and size-sweep evidence support it.
7. Repeat with `--min-ms 50 --samples 9` when a run is noisy. Preserve the earlier
   report and its invalid status instead of discarding it.

## Typical usage patterns

Before optimizing a Python data-processing stage, first prove where time goes and
what work is equivalent. These kernels give you a small setting to practice that
discipline before adding a P3 transcript transform, DuckDB-adjacent preparation
step, JSON processing loop or other real workload.

When a coding agent proposes an optimization, ask for a before/after evidence bundle
and an explanation tied to changed source and machine code. Run `compare` with the
same machine and settings. A faster result with a changed answer or extra hidden
allocation should fail review.

For learning, form a prediction before each run. For example, predict which kernel
will benefit from independent accumulators, then inspect the compiler output and
record whether the result supports your explanation. A prediction that fails is
useful evidence about interpreter costs, compiler optimization or the model.

## Learning plan

| Session | Exercise | Evidence to retain |
| --- | --- | --- |
| 1 | Trace one reduction from Python to Rust and verify input identity | Exact checksums and input digests |
| 2 | Compare one sample with calibrated repeated batches | Raw samples, CV, rejected noisy run |
| 3 | Inspect O0 and O3 reduction loops | Function labels and relevant load/arithmetic instructions |
| 4 | Add a temporary extra copy to one kernel | Allocation regression and a compatible before/after comparison |
| 5 | Sweep sizes 1024, 16384, 262144 and 1048576 for chase/strided | Working-set size versus throughput, with cache caveats |
| 6 | Change a named hardware assumption and predict the ceiling | Explicit assumptions and any MODEL EXCEEDED observations |
| 7 | Add one small synthetic P3-style text or array transform | Reference implementation, golden answer, measurement protocol |

Size sweeps are separate runs. For example:

```sh
uv run reality-check run --out reports/chase-small --workload chase --size 1024
uv run reality-check run --out reports/chase-large --workload chase --size 262144
```

`compare` intentionally rejects those two runs as incompatible regression baselines.
Study their tables as a scaling experiment instead. For before/after code comparisons,
hold size, seed, environment, compiler flags and measurement settings constant.

## Resources

- [Rust black_box](https://doc.rust-lang.org/std/hint/fn.black_box.html) explains the compiler barrier and its limits.
- [rustc output options](https://doc.rust-lang.org/rustc/command-line-arguments.html#--emit-specifies-the-types-of-output-files-to-generate) documents assembly and LLVM output.
- [Python time](https://docs.python.org/3/library/time.html#time.perf_counter_ns) documents the monotonic performance counter.
- [Python tracemalloc](https://docs.python.org/3/library/tracemalloc.html) explains what traced memory measurements include.
- [LLVM vectorizers](https://llvm.org/docs/Vectorizers.html) explains loop and SLP vectorization and optimization remarks.

## Extensions worth building

**P3 performance fixture pack.** Add synthetic transcript normalization, chunk
indexing and batch aggregation workloads. Separate parsing, allocation and I/O so
an agent can identify which optimization is relevant to the actual pipeline.

**Agent optimization review.** Attach a benchmark case and an allocation budget to
each performance PR. Require identical outputs, validated evidence and a human
review of any semantic tradeoff. Keep noisy-run failures distinct from regressions.

**Model calibration notebook.** Add measured bandwidth and latency experiments for
several working-set sizes. Compare those measurements with the illustrative
hardware assumptions. Avoid using one fitted profile to validate the same samples
that produced it; keep a held-out workload.

**Assembly claim checker.** Start with manually annotated function regions, then
test whether an AI explanation cites the correct instructions and acknowledges
uncertainty. Evaluate the explanation independently from whether the code got faster.

**Portable benchmark history.** Store bundles by source hash, compiler and machine
identity. Compare trends only within compatible groups. This could catch toolchain
changes or accidental allocation regressions across your small-project portfolio.

## Limits and troubleshooting

The suite studies small CPU kernels. It is not a universal language ranking,
production capacity prediction or complete profiler. Timing includes validation
and dispatch overhead. The cache state is uncontrolled, allocation probes differ
between languages, and the hardware model is intentionally approximate.

If CPU metadata is unavailable, reports say so and comparisons refuse to establish
compatibility. If files change during a run, start a new run from a stable checkout.
Use a new output directory for every run.

On a synced macOS Documents folder, hidden flags on generated `.pth` files can
prevent Python from loading an editable package. A virtual environment outside the
synced folder avoids that environment problem. For example, set
`UV_PROJECT_ENVIRONMENT=$HOME/.venvs/performance-reality-check-lab` before running uv.
This is a local setup choice and is not required in normal checkouts or CI.
