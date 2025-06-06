# backend/gemini_service.py
import openai
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, UPLOAD_DIR
from models import ProcessedDocument
import uuid
import os
import aiofiles # For asynchronous file operations
import filetype # For robust file type checking
import json
import base64 # For encoding file content for OpenAI API
from typing import List, Dict, Any, Optional

import fitz # Import PyMuPDF

# Configure OpenAI API key
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# In-memory store for processed documents (for demonstration purposes)
# In a real application, you'd use a database (e.g., PostgreSQL, MongoDB, Pinecone for embeddings)
documents_store: dict[str, ProcessedDocument] = {}

async def process_pdf_document(file_content: bytes, filename: str) -> ProcessedDocument:
    """
    Processes a PDF document using OpenAI's vision capabilities by converting pages to images.
    Extracts text and structure, stores it, and returns a ProcessedDocument object.
    """
    # Use filetype to verify MIME type by inspecting the file content
    kind = filetype.guess(file_content)
    if kind is None:
        raise ValueError("Could not determine file type from content.")

    if kind.mime != "application/pdf":
        raise ValueError(f"Unsupported file type: {kind.mime}. Only PDFs are allowed.")

    # Create a unique ID for the document
    doc_id = str(uuid.uuid4())
    
    # --- PDF to Image Conversion using PyMuPDF ---
    image_parts = []
    try:
        pdf_document = fitz.open(stream=file_content, filetype="pdf")
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap() # Render page to pixmap
            img_bytes = pix.pil_tobytes(format="PNG") # Convert pixmap to PNG bytes
            base64_image = base64.b64encode(img_bytes).decode('utf-8')
            image_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": "high" # Use 'high' for more detailed analysis
                },
            })
        pdf_document.close()
    except Exception as e:
        raise ValueError(f"Error converting PDF pages to images: {e}")
    # --- End PDF to Image Conversion ---

    # Example of how you might instruct OpenAI to extract structured content
    prompt_text = f"""
    Analyze the following PDF document.
    Extract the following information:
    - **Title:** The main title of the paper.
    - **Abstract:** The abstract of the paper.
    - **Sections:** A list of sections, where each section has:
        - `title`: The section title.
        - `content`: A summary of the section's text.
        - (Optional) `tables`: If tables are present in the section, describe them or extract key data.
        - (Optional) `figures`: If figures are present, describe them.
    - **References:** A list of references.

    Output the extracted information as a JSON object with the following schema:
    {{
        "title": "...",
        "abstract": "...",
        "sections": [
            {{"title": "...", "content": "...", "tables": [...], "figures": [...]}},
            ...
        ],
        "references": [...]
    }}

    If any element is not found, use an empty string or empty list as appropriate.
    Ensure high accuracy, especially for tables and key results.
    """

    # Combine the initial prompt with all the image parts
    messages_content = [{"type": "text", "text": prompt_text}] + image_parts

    try:
        response = await client.chat.completions.create(
            model="gpt-4o", # Use a vision-capable model like gpt-4o or gpt-4o-mini
            messages=[
                {
                    "role": "user",
                    "content": messages_content, # Pass the combined content
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.0 # Make it deterministic for extraction tasks
        )
        
        extracted_metadata = json.loads(response.choices[0].message.content)

        processed_doc = ProcessedDocument(
            id=doc_id,
            filename=filename,
            extracted_text=extracted_metadata.get("text_content", ""), # A simplified representation
            metadata=extracted_metadata
        )
        documents_store[doc_id] = processed_doc
        return processed_doc

    except Exception as e:
        print(f"Error processing PDF with OpenAI: {e}")
        raise

async def query_document(document_id: str, question: str) -> str:
    """Answers a question based on the content of a specific document."""
    if document_id not in documents_store:
        raise ValueError(f"Document with ID {document_id} not found.")

    doc = documents_store[document_id]
    
    # Construct the prompt using the document's content
    document_content = json.dumps(doc.metadata, indent=2) # Using the structured metadata
    prompt = f"""
    You are an AI assistant specialized in analyzing documents.
    Based on the following document content, answer the user's question.
    If the answer is not explicitly stated in the document, state that you cannot find the information.

    Document Content (structured JSON):
    {document_content}

    User's Question: {question}

    Answer:
    """
    response = await client.chat.completions.create(
        model="gpt-4o", # Using a powerful model for question answering
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2 # Allow some creativity for answering
    )
    return response.choices[0].message.content.strip()

async def summarize_document_section(document_id: str, section_title: Optional[str] = None, granularity: str = "overview") -> str:
    """Summarizes a specific section or the entire document."""
    if document_id not in documents_store:
        raise ValueError(f"Document with ID {document_id} not found.")

    doc = documents_store[document_id]
    
    content_to_summarize = ""
    if section_title:
        found_section = False
        for section in doc.metadata.get("sections", []):
            if section["title"].lower() == section_title.lower():
                content_to_summarize = section["content"]
                found_section = True
                break
        if not found_section:
            raise ValueError(f"Section '{section_title}' not found in document.")
    else:
        # Summarize the entire document by combining abstract and section summaries
        content_to_summarize += doc.metadata.get("abstract", "") + "\n\n"
        for section in doc.metadata.get("sections", []):
            content_to_summarize += f"{section['title']}:\n{section['content']}\n\n"

    if not content_to_summarize.strip():
        return "No content found to summarize."

    prompt = f"""
    Summarize the following content.
    Granularity: {granularity}.

    Content:
    {content_to_summarize}

    Summary:
    """
    response = await client.chat.completions.create(
        model="gpt-4o", # Using a powerful model for summarization
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3 # Some creativity is fine for summarization
    )
    return response.choices[0].message.content.strip()

async def extract_evaluation_results(document_id: str, query: str) -> Dict[str, Any]:
    """Extracts specific evaluation results or key data points."""
    if document_id not in documents_store:
        raise ValueError(f"Document with ID {document_id} not found.")

    doc = documents_store[document_id]
    
    document_content = json.dumps(doc.metadata, indent=2) # Using the structured metadata

    prompt = f"""
    From the following document content, extract specific evaluation results or key data points related to the query: "{query}".
    Focus on numerical values, metrics, and their descriptions.
    Output the extracted information as a JSON object with relevant key-value pairs.
    For example, if the query is "accuracy and F1-score", the output could be:
    {{"accuracy": "95.2%", "f1_score": "0.89"}}
    If the query is "key findings", it could be:
    {{"finding_1": "...", "finding_2": "..."}}
    If no relevant information is found, return an empty JSON object: {{}}.

    Document Content (structured JSON):
    {document_content}

    Extraction Query: {query}

    Extracted Results (JSON):
    """
    response = await client.chat.completions.create(
        model="gpt-4o", # Using a powerful model for extraction
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.0 # Make it very deterministic for extraction
    )
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        print(f"Warning: OpenAI did not return valid JSON for extraction. Raw response: {response.choices[0].message.content}")
        return {"error": "Could not parse extracted results as JSON."}

# This function demonstrates the function calling aspect.
# It doesn't use the OpenAI API directly for the search, but an OpenAI model would call this "tool".
async def arxiv_lookup_tool(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Looks up papers on Arxiv based on a search query.
    This function is designed to be called by the AI agent (via function calling).
    """
    print(f"Simulating Arxiv lookup for: '{query}' with {max_results} results.")
    
    # Using the 'arxiv' library for actual search
    try:
        import arxiv
        search = arxiv.Search(
            query = query,
            max_results = max_results,
            sort_by = arxiv.SortCriterion.Relevance,
            sort_order = arxiv.SortOrder.Descending
        )
        papers_data = []
        for result in search.results():
            papers_data.append({
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "summary": result.summary,
                "url": result.entry_id,
                "published": result.published.isoformat()
            })
        return papers_data
    except Exception as e:
        print(f"Error calling Arxiv API: {e}")
        return []