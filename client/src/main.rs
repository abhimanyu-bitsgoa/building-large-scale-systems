use clap::Parser;
use futures::stream::{self, StreamExt};
use hdrhistogram::Histogram;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::mpsc;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Target URL
    #[arg(short, long, default_value = "http://127.0.0.1:3000/")]
    url: String,

    /// Number of concurrent requests
    #[arg(short, long, default_value_t = 10)]
    concurrency: usize,

    /// Total number of requests
    #[arg(short, long, default_value_t = 100)]
    requests: usize,
}

#[tokio::main]
async fn main() {
    let args = Args::parse();
    let client = reqwest::Client::new();
    let success_count = Arc::new(AtomicUsize::new(0));
    let failure_count = Arc::new(AtomicUsize::new(0));

    println!("Starting load test against {}", args.url);
    println!("Concurrency: {}", args.concurrency);
    println!("Total requests: {}", args.requests);

    let (tx, mut rx) = mpsc::channel(args.requests);
    let start_time = Instant::now();

    let requests = stream::iter(0..args.requests);
    requests
        .for_each_concurrent(args.concurrency, |_| {
            let client = client.clone();
            let url = args.url.clone();
            let success_count = success_count.clone();
            let failure_count = failure_count.clone();
            let tx = tx.clone();
            async move {
                let start = Instant::now();
                match client.get(&url).send().await {
                    Ok(resp) => {
                        let duration = start.elapsed().as_micros() as u64;
                        let _ = tx.send(duration).await;
                        if resp.status().is_success() {
                            success_count.fetch_add(1, Ordering::Relaxed);
                        } else {
                            failure_count.fetch_add(1, Ordering::Relaxed);
                        }
                    }
                    Err(_) => {
                        failure_count.fetch_add(1, Ordering::Relaxed);
                    }
                }
            }
        })
        .await;

    // Drop the original sender so the receiver knows when to stop
    drop(tx);

    let mut hist = Histogram::<u64>::new(3).unwrap();
    while let Some(duration) = rx.recv().await {
        hist.record(duration).unwrap();
    }

    let duration = start_time.elapsed();
    let success = success_count.load(Ordering::Relaxed);
    let failure = failure_count.load(Ordering::Relaxed);

    println!("Load test completed in {:.2?}", duration);
    println!("Successful requests: {}", success);
    println!("Failed requests: {}", failure);
    println!(
        "Requests per second: {:.2}",
        (success + failure) as f64 / duration.as_secs_f64()
    );

    println!("\nLatency Percentiles (µs):");
    println!("P50:  {}", hist.value_at_percentile(50.0));
    println!("P90:  {}", hist.value_at_percentile(90.0));
    println!("P99:  {}", hist.value_at_percentile(99.0));
    println!("Max:  {}", hist.max());

    println!("\nLatency Distribution:");
    // Simple ASCII visualization
    let max_count = hist.iter_linear(1000).map(|iter| iter.count_since_last_iteration()).max().unwrap_or(1);
    for iter in hist.iter_log(1, 2.0) {
        let count = iter.count_since_last_iteration();
        if count > 0 {
            let bar_len = (count as f64 / max_count as f64 * 40.0) as usize;
            let bar: String = "=".repeat(bar_len);
            println!(
                "{:5} µs - {:5} µs | {:4} | {}",
                iter.value_iterated_to() / 2, // Approximate lower bound
                iter.value_iterated_to(),
                count,
                bar
            );
        }
    }
}
