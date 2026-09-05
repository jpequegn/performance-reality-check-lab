use std::hint::black_box;
pub const FORMAT_VERSION: u32 = 1;
pub const WORKLOADS: [&str; 4] = ["reduction", "chase", "strided", "branch"];
pub const VARIANTS: [&str; 3] = ["loop", "unrolled", "allocating"];
pub fn next_word(state: &mut u64) -> u64 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    *state
}
pub fn inputs(workload: &str, size: usize, seed: u64) -> Result<Vec<u64>, String> {
    if !WORKLOADS.contains(&workload) || !(64..=1 << 20).contains(&size) || !size.is_power_of_two()
    {
        return Err("Unknown workload or invalid power-of-two size".into());
    }
    let mut state = if seed == 0 { 1 } else { seed };
    if workload != "chase" {
        return Ok((0..size).map(|_| next_word(&mut state) & 1023).collect());
    }
    let mut order: Vec<usize> = (0..size).collect();
    for i in (1..size).rev() {
        let j = (next_word(&mut state) % (i as u64 + 1)) as usize;
        order.swap(i, j);
    }
    let mut links = vec![0; size];
    for i in 0..size {
        links[order[i]] = order[(i + 1) % size] as u64;
    }
    Ok(links)
}
pub fn input_digest(data: &[u64]) -> u64 {
    data.iter().fold(14695981039346656037u64, |hash, value| {
        (hash ^ value).wrapping_mul(1099511628211)
    })
}
pub type Kernel = fn(&[u64]) -> u64;
pub fn kernel(workload: &str, variant: &str) -> Result<Kernel, String> {
    match (workload, variant) {
        ("reduction", "loop") => Ok(reduction_loop),
        ("reduction", "unrolled") => Ok(reduction_unrolled),
        ("reduction", "allocating") => Ok(reduction_allocating),
        ("chase", "loop") => Ok(chase_loop),
        ("chase", "unrolled") => Ok(chase_unrolled),
        ("chase", "allocating") => Ok(chase_allocating),
        ("strided", "loop") => Ok(strided_loop),
        ("strided", "unrolled") => Ok(strided_unrolled),
        ("strided", "allocating") => Ok(strided_allocating),
        ("branch", "loop") => Ok(branch_loop),
        ("branch", "unrolled") => Ok(branch_unrolled),
        ("branch", "allocating") => Ok(branch_allocating),
        _ => Err("Unknown kernel".into()),
    }
}
#[no_mangle]
#[inline(never)]
pub fn reduction_loop(data: &[u64]) -> u64 {
    let mut total = 0;
    for &x in data {
        total += x;
    }
    total
}
#[no_mangle]
#[inline(never)]
pub fn reduction_unrolled(data: &[u64]) -> u64 {
    let (mut a, mut b, mut c, mut d) = (0, 0, 0, 0);
    for x in data.chunks_exact(4) {
        a += x[0];
        b += x[1];
        c += x[2];
        d += x[3];
    }
    a + b + c + d
}
#[no_mangle]
#[inline(never)]
pub fn chase_loop(data: &[u64]) -> u64 {
    let (mut index, mut total) = (0, 0);
    for _ in 0..data.len() {
        index = data[index] as usize;
        total += index as u64;
    }
    total
}
#[no_mangle]
#[inline(never)]
pub fn chase_unrolled(data: &[u64]) -> u64 {
    let (mut index, mut total) = (0, 0);
    for _ in (0..data.len()).step_by(4) {
        index = data[index] as usize;
        total += index as u64;
        index = data[index] as usize;
        total += index as u64;
        index = data[index] as usize;
        total += index as u64;
        index = data[index] as usize;
        total += index as u64;
    }
    total
}
#[no_mangle]
#[inline(never)]
pub fn strided_loop(data: &[u64]) -> u64 {
    let (mut total, mask) = (0, data.len() - 1);
    for i in 0..data.len() {
        total += data[(i * 4093) & mask];
    }
    total
}
#[no_mangle]
#[inline(never)]
pub fn strided_unrolled(data: &[u64]) -> u64 {
    let (mut a, mut b, mut c, mut d) = (0, 0, 0, 0);
    let mask = data.len() - 1;
    for i in (0..data.len()).step_by(4) {
        a += data[(i * 4093) & mask];
        b += data[((i + 1) * 4093) & mask];
        c += data[((i + 2) * 4093) & mask];
        d += data[((i + 3) * 4093) & mask];
    }
    a + b + c + d
}
#[no_mangle]
#[inline(never)]
pub fn branch_loop(data: &[u64]) -> u64 {
    let mut total = 0;
    for &x in data {
        total += if x & 1 != 0 { x } else { 3 * x };
    }
    total
}
#[no_mangle]
#[inline(never)]
pub fn branch_unrolled(data: &[u64]) -> u64 {
    let (mut a, mut b, mut c, mut d) = (0, 0, 0, 0);
    for x in data.chunks_exact(4) {
        a += if x[0] & 1 != 0 { x[0] } else { 3 * x[0] };
        b += if x[1] & 1 != 0 { x[1] } else { 3 * x[1] };
        c += if x[2] & 1 != 0 { x[2] } else { 3 * x[2] };
        d += if x[3] & 1 != 0 { x[3] } else { 3 * x[3] };
    }
    a + b + c + d
}
#[no_mangle]
#[inline(never)]
pub fn reduction_allocating(data: &[u64]) -> u64 {
    let copied = black_box(data.to_vec());
    reduction_loop(black_box(&copied))
}
#[no_mangle]
#[inline(never)]
pub fn chase_allocating(data: &[u64]) -> u64 {
    let copied = black_box(data.to_vec());
    chase_loop(black_box(&copied))
}
#[no_mangle]
#[inline(never)]
pub fn strided_allocating(data: &[u64]) -> u64 {
    let copied = black_box(data.to_vec());
    strided_loop(black_box(&copied))
}
#[no_mangle]
#[inline(never)]
pub fn branch_allocating(data: &[u64]) -> u64 {
    let copied = black_box(data.to_vec());
    branch_loop(black_box(&copied))
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn equivalent_kernels() {
        for workload in WORKLOADS {
            for size in [64, 128, 4096] {
                let data = inputs(workload, size, 7).unwrap();
                let expected = match workload {
                    "chase" => (size * (size - 1) / 2) as u64,
                    "branch" => data
                        .iter()
                        .map(|x| if x & 1 != 0 { *x } else { 3 * x })
                        .sum(),
                    _ => data.iter().sum(),
                };
                for variant in VARIANTS {
                    assert_eq!(kernel(workload, variant).unwrap()(&data), expected);
                }
            }
        }
    }
    #[test]
    fn invalid_inputs_and_known_rng() {
        assert_eq!(next_word(&mut 1), 1082269761);
        assert!(inputs("reduction", 65, 7).is_err());
        assert!(kernel("reduction", "unknown").is_err());
    }
}
