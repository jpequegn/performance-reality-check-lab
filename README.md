# Performance reality check lab

Compare equivalent Python and Rust kernels, inspect their generated assembly, and
test your performance expectations against measurements and an explicit hardware model.

Implemented from [project-ideas #253](https://github.com/jpequegn/project-ideas/issues/253).
See [the learning and usage guide](PROJECT_GUIDE.md) and [measurement methodology](docs/METHODOLOGY.md).
The [measured example](docs/EXAMPLE_RUN.md) shows a rejected noisy run, a valid
24-case run, and the generated ARM64 instructions behind two workloads.

## Run it

Use a repository checkout with Python 3.12, uv, and Rust 1.92 or newer installed.
Python uses only the standard library at runtime; Rust has no external crates.

```sh
git clone https://github.com/jpequegn/performance-reality-check-lab.git
cd performance-reality-check-lab
uv sync --locked
uv run reality-check run --out reports/first
uv run reality-check inspect reports/first
```

Open `reports/first/report.md`. Each run writes JSON, Markdown, source snapshots,
O0/O3 assembly and LLVM IR, a native executable, compiler commands, and artifact hashes.
The output directory must be new, so earlier evidence is preserved.

The default run measures 24 combinations: four workloads, three variants, and two
languages. Use a smaller selection for a first look:

```sh
uv run reality-check run --out reports/reduction --workload reduction --size 4096
uv run reality-check run --out reports/longer --min-ms 50 --samples 9
```

Exit codes are 0 for a valid run or successful inspection/comparison, 1 for a detected
regression, and 2 for invalid input, missing evidence, incompatible comparison or
failed sample-quality gates. A noisy run still writes its report and explains why
it is invalid. Increase batch duration and rerun while the machine is idle.

## Workloads

| Workload | What to inspect |
| --- | --- |
| reduction | Independent accumulators, vectorization and contiguous access |
| chase | A randomized single-cycle pointer chain with dependent loads |
| strided | A permutation of reads with a 4093-element stride |
| branch | A seeded conditional integer reduction; the compiler may remove machine branches |

Every workload has loop, unrolled and allocating variants. Python and Rust share
input generation, input digests and exact integer answers. The allocating variant
copies its input on each invocation. An ordinary Rust loop may also be vectorized:
variant names describe source structure, not a guaranteed instruction sequence.

## Compare and inspect

```sh
uv run reality-check run --out reports/before --workload reduction --min-ms 50 --samples 9
# Change a kernel, keeping its semantics and the measurement settings.
uv run reality-check run --out reports/after --workload reduction --min-ms 50 --samples 9
uv run reality-check compare reports/before reports/after --slowdown 1.15
```

Comparison requires valid samples and identical CPU/environment, workload keys,
compiler flags, measurement settings and ordering. Source versions may differ.
It detects timing above the selected ratio, extra allocator calls, or a memory
increase greater than 256 bytes. This is a screening threshold, not a statistical
significance test.

## Hardware assumptions

The default profile is hypothetical: 3 GHz, four u64 vector lanes, two vector
operations per cycle, 30 GB/s and eight cycles per dependent load. These values
are not detected from your machine. A measurement above the model estimate marks
the assumptions for review. Warm cache bandwidth can differ greatly from the
illustrative bandwidth value.

```sh
uv run reality-check run --out reports/custom --hardware fixtures/hardware-example.json
```

Edit a separate hardware JSON profile with your assumptions and their source.
The report preserves those assumptions alongside the measurements.

## Development

```sh
uv run ruff check .
cargo fmt --manifest-path rust/Cargo.toml --check
cargo test --manifest-path rust/Cargo.toml
uv run pytest
```

CI runs these checks on Linux with Python 3.12 and Rust 1.92. The lab also runs on
macOS arm64. Windows is not supported by this version. Run the CLI from an editable
repository checkout so the Rust and Python source files are available to capture.
