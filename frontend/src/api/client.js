/**
 * Minimal API Client for Backend Communication
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

async function postFormData(endpoint, formData, fallbackError) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || `${fallbackError} with HTTP ${response.status}`);
  }

  return await response.json();
}

export async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    return {
      status: 'error',
      message: error.message || 'Failed to connect to backend',
    };
  }
}

export async function extractDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  return postFormData('/documents/extract', formData, 'Extraction failed');
}

export async function verifyDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  return postFormData('/documents/verify', formData, 'Verification failed');
}

export async function askDocument(file, question, conversationHistory = []) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('question', question);
  if (conversationHistory && conversationHistory.length > 0) {
    formData.append('conversation_history', JSON.stringify(conversationHistory));
  }
  return postFormData('/documents/ask', formData, 'Q&A failed');
}

export async function detectContradictions(file) {
  const formData = new FormData();
  formData.append('file', file);
  return postFormData('/documents/contradictions', formData, 'Contradiction detection failed');
}

export async function generateAdvocatePack(file) {
  const formData = new FormData();
  formData.append('file', file);
  return postFormData('/documents/advocate-pack', formData, 'Advocate pack generation failed');
}



