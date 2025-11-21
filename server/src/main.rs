use axum::{
    extract::{Path, Json},
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::time::Duration;
use tokio::time::sleep;

#[tokio::main]
async fn main() {
    // Build our application with a route
    let app = Router::new()
        .route("/", get(root))
        .route("/echo", post(echo))
        .route("/delay/:seconds", get(delay));

    // Run it
    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("listening on {}", addr);
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

// basic handler that responds with a static string
async fn root() -> &'static str {
    let n = 10;
    let result = fib(n);
    println!("Fib({}) = {}", n, result);
    "Hello, World!"
}

fn fib(n: u64) -> u64 {
    if n <= 1 {
        return n;
    }
    fib(n - 1) + fib(n - 2)
}

#[derive(Serialize, Deserialize)]
struct EchoPayload {
    message: String,
}

// handler that echoes the JSON body
async fn echo(Json(payload): Json<EchoPayload>) -> Json<EchoPayload> {
    Json(payload)
}

// handler that waits for a specified number of seconds
async fn delay(Path(seconds): Path<u64>) -> String {
    sleep(Duration::from_secs(seconds)).await;
    format!("Waited for {} seconds", seconds)
}
