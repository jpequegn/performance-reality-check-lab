use reality_kernels::{input_digest, inputs, kernel};
use std::{env, hint::black_box};
mod measure;
#[global_allocator]
static ALLOCATOR: measure::CountingAllocator = measure::CountingAllocator;

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 4 && args.len() != 6 {
        return Err("Usage: reality-kernels WORKLOAD VARIANT SIZE SEED".into());
    }
    let size: usize = args[2].parse().map_err(|_| "Invalid size")?;
    let seed: u64 = args[3].parse().map_err(|_| "Invalid seed")?;
    let data = inputs(&args[0], size, seed)?;
    let function = kernel(&args[0], &args[1])?;
    let checksum = black_box(function(black_box(&data)));
    if args.len() == 6 {
        let samples = args[4].parse().map_err(|_| "Invalid sample count")?;
        let min_ms = args[5].parse().map_err(|_| "Invalid duration")?;
        let expected = match args[0].as_str() {
            "chase" => (size * (size - 1) / 2) as u64,
            "branch" => data
                .iter()
                .map(|x| if x & 1 != 0 { *x } else { 3 * x })
                .sum(),
            _ => data.iter().sum(),
        };
        let (timings, repeats, calls, bytes) =
            measure::measure(function, &data, expected, samples, min_ms)?;
        println!("{{\"checksum\":{},\"input_digest\":{},\"batch_ns\":{:?},\"repeats\":{},\"allocation_calls\":{},\"allocation_bytes\":{}}}",checksum,input_digest(&data),timings,repeats,calls,bytes);
        return Ok(());
    }
    println!(
        "{{\"checksum\":{},\"input_digest\":{}}}",
        checksum,
        input_digest(&data)
    );
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{}", error);
        std::process::exit(2);
    }
}
