from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
import aiohttp
from datetime import datetime
import logging
import asyncio

from extractor import AsyncPageExtractor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Web Page Extractor API",
    description="API for extracting page content, text and links",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class PageData(BaseModel):
    url: str
    status_code: Optional[int] = None
    error: Optional[str] = None
    body: Optional[str] = None
    text: Optional[str] = None
    success: bool

class LinksData(BaseModel):
    internal: List[str] = []
    external: List[str] = []

class HomeData(PageData):
    links: LinksData = LinksData()

class ExtractionResult(BaseModel):
    original_url: str
    home_url: Optional[str] = None
    page_data: PageData
    home_data: HomeData
    timing: Dict[str, Any]

class ErrorResponse(BaseModel):
    detail: str
    status_code: int
    url: Optional[str] = None

class BatchExtractionRequest(BaseModel):
    urls: List[HttpUrl]
    timeout: Optional[int] = 30
    max_retries: Optional[int] = 2

class BatchExtractionResult(BaseModel):
    results: List[ExtractionResult]
    successful: int
    failed: int
    total_time: float

# API Endpoints
@app.get("/extract",
         response_model=ExtractionResult,
         responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def extract_page(
    url: str = Query(..., description="URL to extract content from"),
    timeout: int = Query(10, description="Request timeout in seconds"),
    max_retries: int = Query(2, description="Max retries for failed requests")
):
    """Extract content from a single web page with enhanced error handling"""
    async with aiohttp.ClientSession() as session:
        extractor = AsyncPageExtractor(session, timeout, max_retries)
        try:
            data = await extractor.extract_page_data(url)
            return data
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Processing error: {str(e)}"
            )

@app.post("/extract/batch", response_model=BatchExtractionResult)
async def batch_extract(request: BatchExtractionRequest):
    """Extract content from multiple URLs in parallel with enhanced error handling"""
    start_time = datetime.now()
    results = []
    successful = 0
    failed = 0

    async with aiohttp.ClientSession() as session:
        extractor = AsyncPageExtractor(session, request.timeout, request.max_retries)

        tasks = [extractor.extract_page_data(str(url)) for url in request.urls]
        for future in asyncio.as_completed(tasks):
            try:
                result_data = await future
                results.append(result_data)
                successful += 1
            except Exception as e:
                logger.warning(f"Failed to process URL: {str(e)}")
                failed += 1
                continue

    total_time = (datetime.now() - start_time).total_seconds()

    return BatchExtractionResult(
        results=results,
        successful=successful,
        failed=failed,
        total_time=total_time
    )

@app.get("/health")
async def health_check():
    """Service health check"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(ErrorResponse(
            detail=exc.detail,
            status_code=exc.status_code,
            url=request.url.path
        ))
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(ErrorResponse(
            detail="Internal server error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ))
    )