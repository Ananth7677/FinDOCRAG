import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from Controllers.pipeline_controller import router

app = FastAPI(title="FinDocRAG API", version="0.1.0", description="Extract, analyze, clean, chunk, and embed financial reports.")
app.include_router(router)


@app.exception_handler(FileNotFoundError)
async def missing_input_handler(request: Request, exc: FileNotFoundError):
    return JSONResponse(status_code=409, content={"detail": "Required input file is missing. Run the preceding stages first."})


@app.exception_handler(ValueError)
async def invalid_input_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logging.getLogger(__name__).error("Pipeline request failed (%s)", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Pipeline operation failed. Check the input files and server configuration."})


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000)
