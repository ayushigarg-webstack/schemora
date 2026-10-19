/**
 * API Client for FastAPI backend.
 * Provides typed HTTP methods for diagram generation, validation,
 * AST code analysis, pedagogical explanations, and execution tracing.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export class ApiError extends Error {
  constructor(message, status = 0, code = 'UNKNOWN_ERROR', details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch (err) {
    throw new ApiError(
      `Cannot connect to backend server at ${url}. Ensure the FastAPI server is running.`,
      0,
      'NETWORK_ERROR',
      err.message
    );
  }

  // Attempt to parse JSON response body
  let data;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      const rawText = await response.text();
      data = { detail: rawText };
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    let errCode = `HTTP_${response.status}`;
    let errDetails = null;

    if (data) {
      if (typeof data.detail === 'string') {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        // FastAPI / Pydantic validation error array
        message = data.detail
          .map((item) => {
            const loc = Array.isArray(item.loc) ? item.loc.slice(1).join('.') : '';
            const msg = item.msg || item.message || JSON.stringify(item);
            return loc ? `${loc}: ${msg}` : msg;
          })
          .join('; ');
        errDetails = data.detail;
      } else if (data.error) {
        message = data.error.message || message;
        errCode = data.error.code || errCode;
        errDetails = data.error.details || null;
      } else if (data.message) {
        message = data.message;
      }
    }

    throw new ApiError(message, response.status, errCode, errDetails);
  }

  return data;
}

export const api = {
  // Health & diagnostics
  getHealth: () => request('/health'),

  // Diagram services
  getDiagramTypes: () => request('/api/diagram/types'),
  generateDiagram: (text, diagramType = null, layoutDirection = 'TB') =>
    request('/api/diagram/generate', {
      method: 'POST',
      body: JSON.stringify({
        text,
        diagram_type: diagramType || null,
        layout_direction: layoutDirection || 'TB',
      }),
    }),
  validateDiagram: (diagram) =>
    request('/api/diagram/validate', {
      method: 'POST',
      body: JSON.stringify({ diagram }),
    }),

  // Live code explainer services
  getCodeLanguages: () => request('/api/code/languages'),
  analyzeCode: (code, language = 'python', viewMode = 'cfg', layoutDirection = 'TB') =>
    request('/api/code/analyze', {
      method: 'POST',
      body: JSON.stringify({
        code,
        language,
        view_mode: viewMode,
        layout_direction: layoutDirection,
      }),
    }),
  explainCode: (code, language = 'python', lineNumber = null, nodeId = null) =>
    request('/api/code/explain', {
      method: 'POST',
      body: JSON.stringify({
        code,
        language,
        line_number: lineNumber,
        node_id: nodeId,
      }),
    }),
  traceCode: (code, language = 'python', maxSteps = 500, timeoutSeconds = 2.0) =>
    request('/api/code/trace', {
      method: 'POST',
      body: JSON.stringify({
        code,
        language,
        max_steps: maxSteps,
        timeout_seconds: timeoutSeconds,
      }),
    }),
};
