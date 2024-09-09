# main.py
from fastapi import FastAPI
from endpoints.codedetection import router as codedetection_
from endpoints.sortdxcode import router as sorting_
import uvicorn
import argparse

app = FastAPI()

# Include the routers from the endpoints
app.include_router(codedetection_, prefix="/api/v1/detection")
app.include_router(sorting_, prefix="/api/v1/sorting")

@app.get("/")
def read_root():
    return {"message": "Welcome to the CodeGeneration project!"}


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--host", type=str, default="0.0.0.0")
#     parser.add_argument("--port", type=int, default=8000)
#     args = parser.parse_args()
#     uvicorn.run(app, host=args.host, port=args.port, log_level='info')
