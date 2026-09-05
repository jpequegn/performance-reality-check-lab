use reality_kernels::Kernel;
use std::alloc::{GlobalAlloc, Layout, System};
use std::hint::black_box;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

pub struct CountingAllocator;
static CALLS: AtomicU64 = AtomicU64::new(0);
static BYTES: AtomicU64 = AtomicU64::new(0);

// The wrapper delegates allocation and deallocation to the same system allocator.
unsafe impl GlobalAlloc for CountingAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let pointer = unsafe { System.alloc(layout) };
        if !pointer.is_null() {
            CALLS.fetch_add(1, Ordering::Relaxed);
            BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
        }
        pointer
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        unsafe { System.dealloc(pointer, layout) }
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        let result = unsafe { System.realloc(pointer, layout, size) };
        if !result.is_null() {
            CALLS.fetch_add(1, Ordering::Relaxed);
            BYTES.fetch_add(size as u64, Ordering::Relaxed);
        }
        result
    }
}

fn checked(function: Kernel, data: &[u64], expected: u64) -> Result<(), String> {
    if black_box(function(black_box(data))) != expected {
        return Err("Benchmark invalid: checksum mismatch".into());
    }
    Ok(())
}
fn batch(function: Kernel, data: &[u64], expected: u64, repeats: usize) -> Result<u128, String> {
    let start = Instant::now();
    for _ in 0..repeats {
        checked(function, data, expected)?;
    }
    Ok(start.elapsed().as_nanos())
}
pub fn measure(
    function: Kernel,
    data: &[u64],
    expected: u64,
    samples: usize,
    min_ms: f64,
) -> Result<(Vec<u128>, usize, u64, u64), String> {
    if !(3..=31).contains(&samples) || !min_ms.is_finite() || !(1.0..=200.0).contains(&min_ms) {
        return Err("Invalid measurement settings".into());
    }
    for _ in 0..2 {
        checked(function, data, expected)?;
    }
    let mut repeats = 1;
    while (batch(function, data, expected, repeats)? as f64) < min_ms * 1e6 && repeats < 1 << 20 {
        repeats *= 2;
    }
    let mut timings = Vec::with_capacity(samples);
    for _ in 0..samples {
        timings.push(batch(function, data, expected, repeats)?);
    }
    let calls = CALLS.load(Ordering::Relaxed);
    let bytes = BYTES.load(Ordering::Relaxed);
    checked(function, data, expected)?;
    Ok((
        timings,
        repeats,
        CALLS.load(Ordering::Relaxed) - calls,
        BYTES.load(Ordering::Relaxed) - bytes,
    ))
}
