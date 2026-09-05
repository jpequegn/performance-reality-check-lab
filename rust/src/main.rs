use reality_kernels::{input_digest, inputs, kernel};
use std::{env, hint::black_box};

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 4 {
        return Err("Usage: reality-kernels WORKLOAD VARIANT SIZE SEED".into());
    }
    let size: usize = args[2].parse().map_err(|_| "Invalid size")?;
    let seed: u64 = args[3].parse().map_err(|_| "Invalid seed")?;
    let data = inputs(&args[0], size, seed)?;
    let function = kernel(&args[0], &args[1])?;
    let checksum = black_box(function(black_box(&data)));
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
