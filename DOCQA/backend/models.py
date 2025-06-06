# backend/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DocumentUploadResponse(BaseModel):
    filename: str
    message: str
    document_id: str # A unique ID for the processed document

class QuestionRequest(BaseModel):
    document_id: str # The ID of the document to query
    question: str

class AnswerResponse(BaseModel):
    document_id: str
    question: str
    answer: str

class SummarizeRequest(BaseModel):
    document_id: str
    section_title: Optional[str] = None # Optional: summarize a specific section
    granularity: Optional[str] = "overview" # e.g., "overview", "methodology", "conclusion"

class SummaryResponse(BaseModel):
    document_id: str
    section_title: Optional[str]
    summary: str

class ExtractionRequest(BaseModel):
    document_id: str
    query: str # e.g., "accuracy and F1-score", "key findings"

class ExtractionResponse(BaseModel):
    document_id: str
    query: str
    extracted_data: Dict[str, Any] # Flexible dictionary for extracted results

class ArxivSearchRequest(BaseModel):
    query: str
    max_results: int = 5

class ArxivPaper(BaseModel):
    title: str
    authors: List[str]
    summary: str
    url: str
    published: str

class ArxivSearchResponse(BaseModel):
    query: str
    papers: List[ArxivPaper]

# Internal Document Representation (simplified for this example)
# In a real application, you'd store this in a database or a more robust system.
class ProcessedDocument(BaseModel):
    id: str
    filename: str
    extracted_text: str # Could be much more structured, e.g., list of sections, tables etc.
    metadata: Dict[str, Any] = {} # Store title, abstract, sections, etc.