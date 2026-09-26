/**
 * Minimal API Client for Backend Communication
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

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

export async function parseDocument(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/documents/parse`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Upload failed with HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw error;
  }
}

export async function extractDocument(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/documents/extract`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Extraction failed with HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw error;
  }
}

export async function verifyDocument(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/documents/verify`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Verification failed with HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw error;
  }
}

export async function askDocument(file, question, conversationHistory = []) {

  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('question', question);
    if (conversationHistory && conversationHistory.length > 0) {
      formData.append('conversation_history', JSON.stringify(conversationHistory));
    }

    const response = await fetch(`${API_BASE_URL}/documents/ask`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Q&A failed with HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw error;
  }
}


