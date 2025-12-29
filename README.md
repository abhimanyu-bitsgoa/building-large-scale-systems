# building-large-scale-systems

This repository is dedicated to learning how to build large-scale distributed systems from scratch.

> **Note**: The original Rust implementation has been archived to the [`rust-implementation`](../../tree/rust-implementation) branch to facilitate faster prototyping and learning using Python.

## Overview
This project simulates a distributed environment with a Server and Client architecture, designed to explore concepts like latency, concurrency, and API design.

### Features
1.  **CPU Intensive Task**: `GET /` - Calculates Fibonacci(10) to simulate CPU load.
2.  **Protocol Parsing**: `POST /echo` - Strictly types and echoes back a JSON payload using Pydantic models.
3.  **Concurrency Simulation**: `GET /delay/:seconds` - Asynchronously waits for a specified duration, simulating I/O blocking (like a DB call).

## Technology Stack
*   **Language**: Python 3
*   **Server**: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) (High-performance ASGI server).
*   **Client**: [httpx](https://www.python-httpx.org/) (Async HTTP client).
*   **Validation**: [Pydantic](https://docs.pydantic.dev/) (Data validation and settings management).

## Getting Started

### Prerequisites
*   Python 3.8+
*   `pip`

### Installation
1.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Usage

**1. Run the Server**
The server runs on port 3000.
```bash
python server/main.py
```

**2. Run the Client**
Open a new terminal, activate the venv, and run the client verification script.
```bash
python client/client.py
```
