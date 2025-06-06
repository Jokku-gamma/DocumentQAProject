# backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import asyncio # For running async operations
import json

from config import UPLOAD_DIR
from gemini import process_pdf_document, query_document, summarize_document_section, extract_evaluation_results, documents_store, arxiv_lookup_tool
from models import DocumentUploadResponse, QuestionRequest, AnswerResponse, SummarizeRequest, SummaryResponse, ExtractionRequest, ExtractionResponse, ArxivSearchRequest, ArxivSearchResponse, ProcessedDocument

app = FastAPI(
    title="Document Q&A AI Agent",
    description="Backend API for processing documents with Gemini and answering questions.",
    version="1.0.0"
)

# CORS configuration for JavaScript frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend's origin in production (e.g., "http://localhost:3000")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload-document/", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Uploads a PDF document, processes it using Gemini, and stores its extracted content.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    file_content = await file.read()
    try:
        processed_doc = await process_pdf_document(file_content, file.filename)
        return DocumentUploadResponse(
            filename=processed_doc.filename,
            message="Document uploaded and processed successfully.",
            document_id=processed_doc.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")

@app.get("/documents/{document_id}", response_model=ProcessedDocument)
async def get_document_details(document_id: str):
    """
    Retrieves the extracted details of a previously uploaded document.
    """
    if document_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found.")
    return documents_store[document_id]

@app.post("/query-document/", response_model=AnswerResponse)
async def query_document_endpoint(request: QuestionRequest):
    """
    Answers a natural language question based on the content of an uploaded document.
    """
    try:
        answer = await query_document(request.document_id, request.question)
        return AnswerResponse(
            document_id=request.document_id,
            question=request.question,
            answer=answer
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {e}")

@app.post("/summarize-document/", response_model=SummaryResponse)
async def summarize_document_endpoint(request: SummarizeRequest):
    """
    Summarizes a section of a document or the entire document.
    """
    try:
        summary = await summarize_document_section(
            request.document_id, request.section_title, request.granularity
        )
        return SummaryResponse(
            document_id=request.document_id,
            section_title=request.section_title,
            summary=summary
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to summarize document: {e}")


@app.post("/extract-data/", response_model=ExtractionResponse)
async def extract_data_endpoint(request: ExtractionRequest):
    """
    Extracts specific evaluation results or data points from a document.
    """
    try:
        extracted_data = await extract_evaluation_results(request.document_id, request.query)
        return ExtractionResponse(
            document_id=request.document_id,
            query=request.query,
            extracted_data=extracted_data
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract data: {e}")

@app.post("/arxiv-search/", response_model=ArxivSearchResponse)
async def arxiv_search_endpoint(request: ArxivSearchRequest):
    """
    (Bonus) Searches Arxiv for papers based on a query.
    This endpoint will be called by the frontend directly, but its underlying
    logic (`arxiv_lookup_tool`) is what Gemini would call via function calling.
    """
    try:
        papers = await arxiv_lookup_tool(request.query, request.max_results)
        return ArxivSearchResponse(
            query=request.query,
            papers=papers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform Arxiv search: {e}")


# Endpoint for Gemini's function calling (if you were to expose it to a webhook)
# For this project, the Arxiv search is exposed directly to the frontend.
# If Gemini were to be the orchestrator and call external tools, this is where you'd handle it.
# @app.post("/gemini-webhook/")
# async def gemini_webhook(body: dict = Body(...)):
#     """
#     A conceptual endpoint if Gemini were to call back your service
#     with function calls or other results.
#     """
#     # This would involve parsing Gemini's function call request,
#     # executing the appropriate local function (e.g., arxiv_lookup_tool),
#     # and returning the result back to Gemini.
#     # This is more advanced and not strictly needed for the initial setup.
#     pass


if __name__ == "__main__":
    import uvicorn
    # Run the FastAPI application
    # You can access the API documentation at http://127.0.0.1:8000/docs
    uvicorn.run(app, host="127.0.0.1", port=8000)