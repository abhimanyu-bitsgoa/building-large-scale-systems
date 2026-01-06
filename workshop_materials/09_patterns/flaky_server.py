import uvicorn
from fastapi import FastAPI, HTTPException
import argparse

app = FastAPI()
FAILLING = False

@app.get("/")
def home():
    if FAILLING:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return {"status": "ok", "message": "I am healthy!"}

@app.post("/fail")
def toggle_fail():
    global FAILLING
    FAILLING = True
    return {"status": "failing"}

@app.post("/recover")
def toggle_recover():
    global FAILLING
    FAILLING = False
    return {"status": "recovered"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9001)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
