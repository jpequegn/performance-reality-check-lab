# Measurement methodology

## Contract

Case sizes are powers of two from 64 through 1,048,576. Seeds are unsigned 64-bit
integers. A shared xorshift generator produces integer values in 0..1023. The chase
fixture shuffles a permutation and connects it into one cycle. Seed zero uses state
one. A deterministic rolling input digest checks cross-language fixture equality;
artifact provenance uses SHA-256 separately.

Reduction and strided reduction sum the same values. The chase visits each index
exactly once, so its expected sum is n*(n-1)/2. Conditional reduction adds x for odd
values and 3*x for even values. All answers fit in u64 for supported cases.

The unrolled kernels use four accumulators where dependencies allow it. Unrolling
the chase preserves the dependency chain. The allocating kernels explicitly copy
the input. Rust uses black_box around input/output and the allocated copy to
discourage removing the measured work. This is a best-effort compiler mechanism.

## Timing

Input construction and reference calculations precede measurement. There are two
warmups per kernel. Calibration doubles repetitions until the batch reaches the
requested duration or 2^20 repetitions. Each sample times the whole batch using
Python perf_counter_ns or Rust Instant, then divides by repetitions. The samples
include kernel dispatch, loop overhead and a checksum check on every invocation.
Neither includes process startup or compiler time. Python disables cyclic GC for
timed batches and restores its prior state afterward.

The experiment shuffles its schedule with a fixed seed to reduce systematic order
bias. Inputs are reused and caches are not flushed. Frequency, thermals, operating
system scheduling and background work are not controlled. Large size sweeps make
cache effects easier to investigate, but a timing difference alone does not prove
a cache miss rate or a specific bottleneck.

## Quality gates

Raw sample counts, repeat counts and durations must be valid. A batch shorter than
half the requested minimum is invalid. Sample coefficient of variation is sample
standard deviation divided by sample mean; it must not exceed the configured limit.
The default is 0.20. No outliers are dropped. Median, min, p95, throughput and raw
samples remain in the report. `run` and `inspect` return exit code 2 for invalid
sample quality. `compare` refuses an invalid run.

These gates establish a basic measurement protocol. They do not prove unbiased
timings or statistical significance. The 15% default slowdown threshold is a
practical screening policy, not a hypothesis test. Compare repeated runs on an idle
machine before drawing conclusions from a small difference.

## Allocation evidence

Python tracemalloc measures peak traced memory during a separate invocation. It
does not count all allocation calls or report process RSS. Rust wraps the system
allocator and reports the delta in successful allocation/reallocation calls and
requested bytes during a separate invocation. Rust counters remain present in
timed allocating code; their atomic increments are part of that implementation's
measured cost. The two languages' allocation metrics are not directly comparable.

## Compiler evidence

Each run copies the Python and Rust sources. Explicit rustc commands compile the
saved library at O0 and O3 to assembly and LLVM IR. A measured executable is built
from the saved library/main/measurement sources with O3, generic target CPU,
one codegen unit, and debug/overflow checks disabled. Cargo's global configuration
does not control this build. The report records rustc -vV and all commands.

The evidence manifest hashes sources, compiler artifacts and the binary. Inspection
requires the expected artifacts, matching source hashes, matching compiler
metadata, and agreement between raw samples and derived report fields. These
hashes detect accidental changes; they do not authenticate an untrusted author.

Read the function labels linked in the report. SIMD loads and arithmetic within a
loop support a vectorization observation; a SIMD instruction elsewhere in the
file does not. A source-level conditional may become branchless machine code.

## Ceiling model

The model derives an arithmetic-rate estimate from clock * lanes * vector ops/cycle,
a memory estimate from logical bytes / bandwidth, and a serial dependency estimate
for chase from elements * dependent-load cycles / clock. The largest modeled time
sets the estimated ideal duration. Allocation adds one read/write copy pass, for
24 logical bytes per element instead of 8. Conditional reduction uses three
arithmetic operations per element as a proxy, not an instruction count.

The model omits cache hierarchy, Python object layout, interpreter overhead,
allocation machinery, branches and detailed instruction throughput. Its inputs
are assumptions, not automatic hardware measurements. `MODEL EXCEEDED` is evidence
that those assumptions need reconsideration; it does not invalidate a correctly
measured timing or prove impossible hardware performance.
