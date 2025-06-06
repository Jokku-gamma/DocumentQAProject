const API_BASE_URL = 'http://127.0.0.1:8000'; // Make sure this matches your FastAPI server address

let currentDocumentId = null; // Store the ID of the currently processed document

// --- Helper Functions ---
function updateDocumentIdDisplay(docId) {
    document.getElementById('currentDocumentId').textContent = docId || 'N/A';
    document.getElementById('currentDocumentId2').textContent = docId || 'N/A';
    document.getElementById('currentDocumentId3').textContent = docId || 'N/A';
}

function showStatus(elementId, message, isError = false) {
    const statusDiv = document.getElementById(elementId);
    statusDiv.textContent = message;
    statusDiv.className = `status ${isError ? 'error' : 'success'}`;
    statusDiv.style.display = 'block';
}

function clearStatus(elementId) {
    const statusDiv = document.getElementById(elementId);
    statusDiv.textContent = '';
    statusDiv.className = 'status';
    statusDiv.style.display = 'none';
}

// --- Event Listeners ---

// Upload Document
document.getElementById('uploadBtn').addEventListener('click', async () => {
    const pdfFile = document.getElementById('pdfUpload').files[0];
    if (!pdfFile) {
        showStatus('uploadStatus', 'Please select a PDF file first.', true);
        return;
    }

    clearStatus('uploadStatus');
    showStatus('uploadStatus', 'Uploading and processing document...', false);
    document.getElementById('documentIdDisplay').textContent = '';

    const formData = new FormData();
    formData.append('file', pdfFile);

    try {
        const response = await fetch(`${API_BASE_URL}/upload-document/`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (response.ok) {
            currentDocumentId = data.document_id;
            updateDocumentIdDisplay(currentDocumentId);
            showStatus('uploadStatus', data.message, false);
            document.getElementById('documentIdDisplay').textContent = `Document ID: ${data.document_id}`;
        } else {
            showStatus('uploadStatus', `Error: ${data.detail || 'Unknown error during upload.'}`, true);
            currentDocumentId = null;
            updateDocumentIdDisplay(currentDocumentId);
        }
    } catch (error) {
        console.error('Upload failed:', error);
        showStatus('uploadStatus', `Network error or server unavailable: ${error.message}`, true);
        currentDocumentId = null;
        updateDocumentIdDisplay(currentDocumentId);
    }
});

// Ask a Question
document.getElementById('askQuestionBtn').addEventListener('click', async () => {
    if (!currentDocumentId) {
        showStatus('answerDisplay', 'Please upload and process a document first.', true);
        return;
    }

    const question = document.getElementById('questionInput').value;
    if (!question.trim()) {
        showStatus('answerDisplay', 'Please enter a question.', true);
        return;
    }

    clearStatus('answerDisplay');
    document.getElementById('answerDisplay').textContent = 'Thinking...';

    try {
        const response = await fetch(`${API_BASE_URL}/query-document/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ document_id: currentDocumentId, question: question }),
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('answerDisplay').textContent = data.answer;
        } else {
            document.getElementById('answerDisplay').textContent = `Error: ${data.detail || 'Failed to get answer.'}`;
            document.getElementById('answerDisplay').classList.add('error');
        }
    } catch (error) {
        console.error('Query failed:', error);
        document.getElementById('answerDisplay').textContent = `Network error or server unavailable: ${error.message}`;
        document.getElementById('answerDisplay').classList.add('error');
    }
});

// Summarize Document/Section
document.getElementById('summarizeBtn').addEventListener('click', async () => {
    if (!currentDocumentId) {
        showStatus('summaryDisplay', 'Please upload and process a document first.', true);
        return;
    }

    const sectionTitle = document.getElementById('summarizeSectionInput').value.trim();
    const granularity = document.getElementById('summarizeGranularity').value;

    clearStatus('summaryDisplay');
    document.getElementById('summaryDisplay').textContent = 'Generating summary...';

    const requestBody = {
        document_id: currentDocumentId,
        granularity: granularity,
    };
    if (sectionTitle) {
        requestBody.section_title = sectionTitle;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/summarize-document/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('summaryDisplay').textContent = data.summary;
        } else {
            document.getElementById('summaryDisplay').textContent = `Error: ${data.detail || 'Failed to generate summary.'}`;
            document.getElementById('summaryDisplay').classList.add('error');
        }
    } catch (error) {
        console.error('Summarization failed:', error);
        document.getElementById('summaryDisplay').textContent = `Network error or server unavailable: ${error.message}`;
        document.getElementById('summaryDisplay').classList.add('error');
    }
});

// Extract Specific Data
document.getElementById('extractBtn').addEventListener('click', async () => {
    if (!currentDocumentId) {
        showStatus('extractionDisplay', 'Please upload and process a document first.', true);
        return;
    }

    const query = document.getElementById('extractQueryInput').value;
    if (!query.trim()) {
        showStatus('extractionDisplay', 'Please enter a query for extraction.', true);
        return;
    }

    clearStatus('extractionDisplay');
    document.getElementById('extractionDisplay').textContent = 'Extracting data...';

    try {
        const response = await fetch(`${API_BASE_URL}/extract-data/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ document_id: currentDocumentId, query: query }),
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('extractionDisplay').textContent = JSON.stringify(data.extracted_data, null, 2);
        } else {
            document.getElementById('extractionDisplay').textContent = `Error: ${data.detail || 'Failed to extract data.'}`;
            document.getElementById('extractionDisplay').classList.add('error');
        }
    } catch (error) {
        console.error('Extraction failed:', error);
        document.getElementById('extractionDisplay').textContent = `Network error or server unavailable: ${error.message}`;
        document.getElementById('extractionDisplay').classList.add('error');
    }
});

// Arxiv Search
document.getElementById('arxivSearchBtn').addEventListener('click', async () => {
    const query = document.getElementById('arxivQueryInput').value;
    const maxResults = document.getElementById('arxivMaxResults').value;

    if (!query.trim()) {
        showStatus('arxivResultsDisplay', 'Please enter a search query for Arxiv.', true);
        return;
    }

    clearStatus('arxivResultsDisplay');
    document.getElementById('arxivResultsDisplay').innerHTML = 'Searching Arxiv...';

    try {
        const response = await fetch(`${API_BASE_URL}/arxiv-search/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query, max_results: parseInt(maxResults) }),
        });

        const data = await response.json();

        if (response.ok) {
            const resultsDiv = document.getElementById('arxivResultsDisplay');
            resultsDiv.innerHTML = ''; // Clear previous results
            if (data.papers && data.papers.length > 0) {
                data.papers.forEach(paper => {
                    const paperDiv = document.createElement('div');
                    paperDiv.classList.add('arxiv-paper');
                    paperDiv.innerHTML = `
                        <h3><a href="${paper.url}" target="_blank">${paper.title}</a></h3>
                        <p><strong>Authors:</strong> ${paper.authors.join(', ')}</p>
                        <p><strong>Published:</strong> ${new Date(paper.published).toLocaleDateString()}</p>
                        <p>${paper.summary.substring(0, 200)}...</p>
                    `;
                    resultsDiv.appendChild(paperDiv);
                });
            } else {
                resultsDiv.textContent = 'No papers found for this query.';
            }
        } else {
            document.getElementById('arxivResultsDisplay').textContent = `Error: ${data.detail || 'Failed to search Arxiv.'}`;
            document.getElementById('arxivResultsDisplay').classList.add('error');
        }
    } catch (error) {
        console.error('Arxiv search failed:', error);
        document.getElementById('arxivResultsDisplay').textContent = `Network error or server unavailable: ${error.message}`;
        document.getElementById('arxivResultsDisplay').classList.add('error');
    }
});

// Initialize document ID display on load
updateDocumentIdDisplay(currentDocumentId);