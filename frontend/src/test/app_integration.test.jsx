import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import App from '../App';
import { api } from '../api/client';

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    getHealth: vi.fn(),
    generateDiagram: vi.fn(),
    analyzeCode: vi.fn(),
    explainCode: vi.fn(),
    traceCode: vi.fn(),
    validateDiagram: vi.fn(),
  },
}));

describe('App Workspace Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getHealth.mockResolvedValue({ status: 'ok', version: '1.0.0' });
  });

  it('renders application workspace with TopNav, LeftPanel, and DiagramCanvas', async () => {
    render(<App />);

    expect(screen.getByDisplayValue('AI Diagram Canvas')).toBeDefined();
    expect(screen.getAllByText('Text to Diagram').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Explain Code')).toBeDefined();
    expect(screen.getByRole('button', { name: /Generate Diagram/i })).toBeDefined();

    // Verify backend online badge updates after health check
    await waitFor(() => {
      expect(screen.getByText('API Online')).toBeDefined();
    });
  });

  it('switches between Text to Diagram and Explain Code modes', () => {
    render(<App />);

    // Default mode is text
    expect(screen.getByText('Natural Language Prompt')).toBeDefined();

    // Switch to code mode
    fireEvent.click(screen.getByText('Explain Code'));
    expect(screen.getByText('Code Analysis & Trace')).toBeDefined();
    expect(screen.getByRole('button', { name: /Analyze CFG/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Run Sandbox Trace/i })).toBeDefined();

    // Switch back to text mode
    fireEvent.click(screen.getByText('Text to Diagram'));
    expect(screen.getByText('Natural Language Prompt')).toBeDefined();
  });

  it('handles backend diagram generation on prompt submission', async () => {
    const mockDiagramResp = {
      diagram: {
        id: 'diag-1',
        diagram_type: 'flowchart',
        layout_direction: 'TB',
        nodes: [
          { id: 'node_start', label: 'Submit Login Form', type: 'terminal', position: { x: 50, y: 50 } },
          { id: 'node_check', label: 'Credentials Valid?', type: 'decision', position: { x: 50, y: 150 } },
          { id: 'node_jwt', label: 'Issue JWT Token', type: 'process', position: { x: 50, y: 250 } },
        ],
        relationships: [
          { id: 'rel_1', source: 'node_start', target: 'node_check', label: '', type: 'sequence' },
          { id: 'rel_2', source: 'node_check', target: 'node_jwt', label: 'Yes', type: 'branch' },
        ],
      },
      classification: {
        predicted_type: 'flowchart',
        confidence: 0.95,
        model: 'TF-IDF Logistic Regression',
        uncertainty_flag: false,
      },
      validation: {
        is_valid: true,
        warnings: [],
      },
    };

    api.generateDiagram.mockResolvedValueOnce(mockDiagramResp);

    render(<App />);

    // Click generate diagram
    const genBtn = screen.getByRole('button', { name: /Generate Diagram/i });
    fireEvent.click(genBtn);

    await waitFor(() => {
      expect(api.generateDiagram).toHaveBeenCalled();
    });
  });

  it('validates that prompt is not empty before generating', async () => {
    render(<App />);

    const textarea = screen.getByPlaceholderText(/Describe your workflow/i);
    fireEvent.change(textarea, { target: { value: '' } });

    const genBtn = screen.getByRole('button', { name: /Generate Diagram/i });
    fireEvent.click(genBtn);

    expect(screen.getByText(/Please enter a natural language prompt/i)).toBeDefined();
    expect(api.generateDiagram).not.toHaveBeenCalled();
  });

  it('validates that prompt meets minimum character length', async () => {
    render(<App />);

    const textarea = screen.getByPlaceholderText(/Describe your workflow/i);
    fireEvent.change(textarea, { target: { value: 'abc' } });

    const genBtn = screen.getByRole('button', { name: /Generate Diagram/i });
    fireEvent.click(genBtn);

    expect(screen.getByText(/Prompt must be at least 5 characters long/i)).toBeDefined();
    expect(api.generateDiagram).not.toHaveBeenCalled();
  });

  it('parses real FastAPI response schema and updates inspector counts and warnings', async () => {
    const realBackendResp = {
      success: true,
      diagram: {
        id: 'real-diag-101',
        diagram_type: 'flowchart',
        version: '2.0.0',
        nodes: [
          { id: 'start_node', label: 'Start', type: 'terminal', position: { x: 320, y: 60 } },
          { id: 'login_form', label: 'User submits login form', type: 'process', position: { x: 320, y: 160 } },
          { id: 'decision_valid', label: 'Credentials Valid?', type: 'decision', position: { x: 320, y: 260 } },
          { id: 'jwt_token', label: 'Issue JWT Token', type: 'process', position: { x: 200, y: 380 } },
        ],
        edges: [
          { id: 'e1', source: 'start_node', target: 'login_form', label: '', edge_type: 'flow', directed: true },
          { id: 'e2', source: 'login_form', target: 'decision_valid', label: '', edge_type: 'flow', directed: true },
          { id: 'e3', source: 'decision_valid', target: 'jwt_token', label: 'Yes', edge_type: 'branch', directed: true },
        ],
        warnings: [],
        layout_config: { direction: 'TB', strategy: 'layered_sugiyama' },
      },
      diagram_type: 'flowchart',
      confidence: 0.94,
      warnings: [
        { code: 'W_RETRY_LOOP', message: 'Retry counter is unconstrained', level: 'warning' },
      ],
      execution_time_ms: 18.5,
    };

    api.generateDiagram.mockResolvedValueOnce(realBackendResp);

    render(<App />);

    const genBtn = screen.getByRole('button', { name: /Generate Diagram/i });
    fireEvent.click(genBtn);

    await waitFor(() => {
      expect(api.generateDiagram).toHaveBeenCalledWith(
        expect.stringContaining('User submits login form'),
        'flowchart',
        'TB'
      );
    });

    // Inspector should update node and edge counts
    await waitFor(() => {
      expect(screen.getByText('4')).toBeDefined(); // 4 nodes
      expect(screen.getByText('3')).toBeDefined(); // 3 edges
    });

    // Warning count pill should appear
    expect(screen.getByText('1')).toBeDefined();
  });

  it('prevents duplicate generation submissions while request is pending', async () => {
    let resolveApi;
    const pendingPromise = new Promise((resolve) => {
      resolveApi = resolve;
    });
    api.generateDiagram.mockReturnValueOnce(pendingPromise);

    render(<App />);

    const genBtn = screen.getByRole('button', { name: /Generate Diagram/i });
    fireEvent.click(genBtn);

    // Button should now be disabled and show loading state
    expect(screen.getByText(/Analyzing & Synthesizing/i)).toBeDefined();
    expect(genBtn.disabled).toBe(true);

    // Clicking again should not trigger another call
    fireEvent.click(genBtn);
    expect(api.generateDiagram).toHaveBeenCalledTimes(1);

    resolveApi({
      success: true,
      diagram: { nodes: [], edges: [] },
      diagram_type: 'flowchart',
      confidence: 0.9,
      warnings: [],
      execution_time_ms: 5,
    });
  });

  it('handles backend error gracefully when API is unavailable', async () => {
    api.generateDiagram.mockRejectedValueOnce(
      new Error('Cannot connect to backend server at /api/diagram/generate')
    );

    render(<App />);

    const genBtn = screen.getByRole('button', { name: /Generate Diagram/i });
    fireEvent.click(genBtn);

    await waitFor(() => {
      expect(screen.getByText(/Cannot connect to backend server/i)).toBeDefined();
    });
  });

  it('performs code analysis and execution trace playback', async () => {
    const mockAnalyzeResp = {
      diagram: {
        id: 'code-ast-1',
        diagram_type: 'flowchart',
        nodes: [
          {
            id: 'stmt_1',
            label: 'def factorial(n):',
            type: 'code',
            source_location: { line_start: 1, line_end: 1 },
          },
          {
            id: 'stmt_2',
            label: 'if n <= 1: return 1',
            type: 'code',
            source_location: { line_start: 2, line_end: 3 },
          },
        ],
        relationships: [],
      },
      validation: { is_valid: true, warnings: [] },
    };

    const mockTraceResp = {
      events: [
        {
          step_id: 1,
          line_number: 1,
          event_type: 'call',
          function_name: 'factorial',
          call_stack: ['<module>', 'factorial(3)'],
          variables: { n: 3 },
          explanation: 'Function factorial invoked with n=3',
        },
        {
          step_id: 2,
          line_number: 2,
          event_type: 'line',
          function_name: 'factorial',
          call_stack: ['<module>', 'factorial(3)'],
          variables: { n: 3 },
          explanation: 'Evaluating condition: n <= 1 -> False',
        },
      ],
      total_steps: 2,
    };

    api.analyzeCode.mockResolvedValueOnce(mockAnalyzeResp);
    api.traceCode.mockResolvedValueOnce(mockTraceResp);

    render(<App />);

    // Switch to code mode
    fireEvent.click(screen.getByText('Explain Code'));

    // Trigger Run Sandbox Trace
    const traceBtn = screen.getByRole('button', { name: /Run Sandbox Trace/i });
    fireEvent.click(traceBtn);

    await waitFor(() => {
      expect(api.traceCode).toHaveBeenCalled();
      expect(screen.getByText('Function factorial invoked with n=3')).toBeDefined();
      expect(screen.getByText('Step 1 / 2')).toBeDefined();
    });
  });
});
