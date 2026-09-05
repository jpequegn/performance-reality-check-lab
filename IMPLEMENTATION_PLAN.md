# Implementation plan

Source: https://github.com/jpequegn/project-ideas/issues/253

Python 3.12 orchestrates dependency-free Rust kernels. Both languages use the same
seeded inputs and exact integer answers. The runtime package uses only the Python
standard library; uv manages pytest and Ruff for development.

## Workloads and measurement

Implement reduction, a dependent pointer chase, strided reduction and a conditional
reduction. Each has loop, unrolled and allocating variants. Unrolled code is
eligible for vectorization; assembly evidence determines what the compiler emitted.
Warmups and calibrated batches isolate kernel timing from process startup and input
construction. Check every returned answer. Measure allocation evidence separately
from timed samples, since instrumentation affects timings.

Record CPU/OS, Python and Rust versions, input size/seed, exact compiler commands,
source/binary/artifact hashes, raw samples, variance and quality status. Fail loudly
on invalid results. No fixed language ranking or machine-independent speed claims.

## Evidence and model

Emit O0 and O3 assembly and LLVM IR for the same library. Build the measured Rust
binary with explicit release settings. Hardware ceilings require named assumptions
for clock, vector lanes, operations/cycle, bandwidth and dependent-load latency.
The included profile is illustrative and must not be presented as detected hardware.

Reports link measurements, compiler artifacts and source evidence. Regression
comparison requires matching inputs, environment and measurement settings; source
hashes may differ. Expose noise and allocation increases, never hide invalid runs.

## Eight tasks

1. Python/Rust package tooling and CI.
2. Deterministic Python fixtures and kernels.
3. Equivalent Rust kernels and cross-language checks.
4. Timing, allocations and quality gates.
5. Assembly/LLVM evidence and hashes.
6. Explicit hardware-ceiling model.
7. CLI reports and compatible regression comparison.
8. Integration evidence and usage/learning guide.

Each task gets one issue and PR. Complete all eight, verify main in a fresh clone,
then close the source issue with repository, verification and usage links.
