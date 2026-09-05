"""Exact integer kernels. Setup and reference answers are outside timed regions."""

from dataclasses import dataclass

WORKLOADS = ("reduction", "chase", "strided", "branch")
VARIANTS = ("loop", "unrolled", "allocating")
MASK = (1 << 64) - 1


@dataclass(frozen=True)
class Case:
    workload: str
    size: int = 4096
    seed: int = 7

    def __post_init__(self):
        if self.workload not in WORKLOADS:
            raise ValueError("Unknown workload")
        if type(self.size) is not int or not 64 <= self.size <= 1 << 20:
            raise ValueError("Size must be an integer from 64 to 1048576")
        if self.size & (self.size - 1):
            raise ValueError("Size must be a power of two")
        if type(self.seed) is not int or not 0 <= self.seed <= MASK:
            raise ValueError("Seed must be an unsigned 64-bit integer")


def random_words(seed):
    state = seed or 1
    while True:
        state ^= (state << 13) & MASK
        state ^= state >> 7
        state ^= (state << 17) & MASK
        yield state


def inputs(case: Case) -> list[int]:
    words = random_words(case.seed)
    if case.workload != "chase":
        return [next(words) & 1023 for _ in range(case.size)]
    order = list(range(case.size))
    for i in range(case.size - 1, 0, -1):
        j = next(words) % (i + 1)
        order[i], order[j] = order[j], order[i]
    links = [0] * case.size
    for i, current in enumerate(order):
        links[current] = order[(i + 1) % case.size]
    return links


def reference(case, data):
    if case.workload == "chase":
        return case.size * (case.size - 1) // 2
    if case.workload == "branch":
        return sum(x if x & 1 else 3 * x for x in data)
    return sum(data)


def input_digest(data):
    value = 14695981039346656037
    for word in data:
        value = ((value ^ word) * 1099511628211) & MASK
    return value


def reduction_loop(data):
    total = 0
    for value in data:
        total += value
    return total


def reduction_unrolled(data):
    a = b = c = d = 0
    for i in range(0, len(data), 4):
        a += data[i]
        b += data[i + 1]
        c += data[i + 2]
        d += data[i + 3]
    return a + b + c + d


def chase_loop(data):
    index = total = 0
    for _ in range(len(data)):
        index = data[index]
        total += index
    return total


def chase_unrolled(data):
    index = total = 0
    for _ in range(0, len(data), 4):
        index = data[index]
        total += index
        index = data[index]
        total += index
        index = data[index]
        total += index
        index = data[index]
        total += index
    return total


def strided_loop(data):
    total = 0
    mask = len(data) - 1
    for i in range(len(data)):
        total += data[(i * 4093) & mask]
    return total


def strided_unrolled(data):
    a = b = c = d = 0
    mask = len(data) - 1
    for i in range(0, len(data), 4):
        a += data[(i * 4093) & mask]
        b += data[((i + 1) * 4093) & mask]
        c += data[((i + 2) * 4093) & mask]
        d += data[((i + 3) * 4093) & mask]
    return a + b + c + d


def branch_loop(data):
    total = 0
    for x in data:
        total += x if x & 1 else 3 * x
    return total


def branch_unrolled(data):
    a = b = c = d = 0
    for i in range(0, len(data), 4):
        x, y, z, w = data[i], data[i + 1], data[i + 2], data[i + 3]
        a += x if x & 1 else 3 * x
        b += y if y & 1 else 3 * y
        c += z if z & 1 else 3 * z
        d += w if w & 1 else 3 * w
    return a + b + c + d


def kernel(workload, variant):
    if workload not in WORKLOADS or variant not in VARIANTS:
        raise ValueError("Unknown kernel")
    base = globals()[f"{workload}_{'loop' if variant == 'allocating' else variant}"]
    if variant == "allocating":
        return lambda data: base(data.copy())
    return base
