import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import TopNav from '../components/TopNav';
import LeftPanel from '../components/LeftPanel';
import RightPanel from '../components/RightPanel';
import PlaybackBar from '../components/PlaybackBar';
import CodeEditor from '../components/CodeEditor';
import { SAMPLE_PROMPTS, SAMPLE_CODE_SNIPPETS } from '../constants/samples';

describe('TopNav Component', () => {
  it('renders application branding, document title, and mode switchers', () => {
    const setTitle = vi.fn();
    const setMode = vi.fn();
    render(
      <TopNav
        mode="text"
        setMode={setMode}
        title="My Architecture"
        setTitle={setTitle}
        isDirty={false}
        backendOnline={true}
        canUndo={false}
        canRedo={false}
      />
    );

    expect(screen.getByDisplayValue('My Architecture')).toBeDefined();
    expect(screen.getByText('Text to Diagram')).toBeDefined();
    expect(screen.getByText('Explain Code')).toBeDefined();
    expect(screen.getByText('API Online')).toBeDefined();
    expect(screen.getByText('Clean')).toBeDefined();

    // Mode switch click
    fireEvent.click(screen.getByText('Explain Code'));
    expect(setMode).toHaveBeenCalledWith('code');
  });

  it('shows modified indicator when document is dirty', () => {
    render(
      <TopNav
        mode="text"
        setMode={vi.fn()}
        title="Unsaved Diagram"
        setTitle={vi.fn()}
        isDirty={true}
        backendOnline={false}
      />
    );

    expect(screen.getByText('Modified')).toBeDefined();
    expect(screen.getByText('API Offline')).toBeDefined();
  });
});

describe('LeftPanel Component', () => {
  it('renders prompt input, type selector, and generation CTA in text mode', () => {
    const setPromptText = vi.fn();
    const setDiagramType = vi.fn();
    const onGenerate = vi.fn();

    render(
      <LeftPanel
        mode="text"
        isCollapsed={false}
        setIsCollapsed={vi.fn()}
        promptText="User logs in to web app"
        setPromptText={setPromptText}
        diagramType="flowchart"
        setDiagramType={setDiagramType}
        layoutDirection="TB"
        setLayoutDirection={vi.fn()}
        onGenerateDiagram={onGenerate}
        isGenerating={false}
        codeLanguage="python"
        codeViewMode="cfg"
      />
    );

    expect(screen.getByText('Text to Diagram')).toBeDefined();
    expect(screen.getByDisplayValue('User logs in to web app')).toBeDefined();
    expect(screen.getByRole('button', { name: /Generate Diagram/i })).toBeDefined();

    // Trigger generate click
    fireEvent.click(screen.getByRole('button', { name: /Generate Diagram/i }));
    expect(onGenerate).toHaveBeenCalled();
  });

  it('renders code editor and analysis buttons in code mode', () => {
    const onAnalyze = vi.fn();
    const onTrace = vi.fn();

    render(
      <LeftPanel
        mode="code"
        isCollapsed={false}
        setIsCollapsed={vi.fn()}
        code={SAMPLE_CODE_SNIPPETS[0].code}
        setCode={vi.fn()}
        codeLanguage="python"
        codeViewMode="cfg"
        setCodeViewMode={vi.fn()}
        onAnalyzeCode={onAnalyze}
        isAnalyzing={false}
        onTraceCode={onTrace}
        isTracing={false}
        onExplainCode={vi.fn()}
        isExplaining={false}
      />
    );

    expect(screen.getByText('Code Analysis & Trace')).toBeDefined();
    expect(screen.getByText('PYTHON 3.10+')).toBeDefined();
    expect(screen.getByRole('button', { name: /Analyze CFG/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Run Sandbox Trace/i })).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: /Analyze CFG/i }));
    expect(onAnalyze).toHaveBeenCalled();
  });

  it('displays error messages when provided', () => {
    const onClear = vi.fn();
    render(
      <LeftPanel
        mode="text"
        isCollapsed={false}
        setIsCollapsed={vi.fn()}
        promptText=""
        setPromptText={vi.fn()}
        diagramType=""
        setDiagramType={vi.fn()}
        layoutDirection="TB"
        setLayoutDirection={vi.fn()}
        onGenerateDiagram={vi.fn()}
        isGenerating={false}
        codeLanguage="python"
        codeViewMode="cfg"
        errorMessage="Syntax error in source AST."
        onClearError={onClear}
      />
    );

    expect(screen.getByText('Syntax error in source AST.')).toBeDefined();
    fireEvent.click(screen.getByLabelText('Dismiss error'));
    expect(onClear).toHaveBeenCalled();
  });
});

describe('RightPanel Component', () => {
  it('displays selected node properties and allows editing labels and types', () => {
    const onUpdateLabel = vi.fn();
    const onUpdateType = vi.fn();
    const onDelete = vi.fn();

    const mockNode = {
      id: 'node_1',
      data: {
        label: 'Process Payment',
        nodeType: 'process',
      },
      position: { x: 120, y: 80 },
    };

    render(
      <RightPanel
        isCollapsed={false}
        setIsCollapsed={vi.fn()}
        selectedNode={mockNode}
        selectedEdge={null}
        onUpdateNodeLabel={onUpdateLabel}
        onUpdateNodeType={onUpdateType}
        onUpdateEdgeLabel={vi.fn()}
        onDeleteSelected={onDelete}
        activeTab="inspector"
        setActiveTab={vi.fn()}
      />
    );

    expect(screen.getByText('node_1')).toBeDefined();
    const labelInput = screen.getByDisplayValue('Process Payment');
    expect(labelInput).toBeDefined();

    fireEvent.change(labelInput, { target: { value: 'Authorize Payment' } });
    expect(onUpdateLabel).toHaveBeenCalledWith('node_1', 'Authorize Payment');

    const typeSelect = screen.getByDisplayValue('Process / Action');
    fireEvent.change(typeSelect, { target: { value: 'decision' } });
    expect(onUpdateType).toHaveBeenCalledWith('node_1', 'decision');
  });

  it('renders pedagogical explanation content in explanation tab', () => {
    const explanationData = {
      summary: 'Computes factorial recursively until n <= 1.',
      steps: ['Check base case n <= 1', 'Multiply n by factorial(n - 1)'],
      complexity: 'O(N) time and stack space',
      beginner_tips: ['Recursion requires a base condition to avoid stack overflow.'],
    };

    render(
      <RightPanel
        isCollapsed={false}
        setIsCollapsed={vi.fn()}
        selectedNode={null}
        selectedEdge={null}
        explanationData={explanationData}
        activeTab="explanation"
        setActiveTab={vi.fn()}
      />
    );

    expect(screen.getByText('Concept Summary')).toBeDefined();
    expect(screen.getByText('Computes factorial recursively until n <= 1.')).toBeDefined();
    expect(screen.getByText('Check base case n <= 1')).toBeDefined();
    expect(screen.getByText('O(N) time and stack space')).toBeDefined();
  });
});

describe('PlaybackBar Component', () => {
  const sampleEvents = [
    {
      step_id: 1,
      line_number: 1,
      event_type: 'call',
      function_name: 'factorial',
      call_stack: ['<module>', 'factorial(3)'],
      variables: { n: 3 },
      explanation: 'Function factorial called with argument n=3',
    },
    {
      step_id: 2,
      line_number: 2,
      event_type: 'line',
      function_name: 'factorial',
      call_stack: ['<module>', 'factorial(3)'],
      variables: { n: 3 },
      explanation: 'Evaluating condition: n <= 1',
    },
  ];

  it('renders step navigation, active line explanations, and variable inspector', () => {
    const onStepForward = vi.fn();
    const onStepBack = vi.fn();
    const onPlay = vi.fn();

    render(
      <PlaybackBar
        traceEvents={sampleEvents}
        currentStep={0}
        isPlaying={false}
        playbackSpeed={1}
        onPlay={onPlay}
        onPause={vi.fn()}
        onStepBack={onStepBack}
        onStepForward={onStepForward}
        onReset={vi.fn()}
        onSeek={vi.fn()}
        onSpeedChange={vi.fn()}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText('Step 1 / 2')).toBeDefined();
    expect(screen.getByText('Function factorial called with argument n=3')).toBeDefined();
    expect(screen.getByText('Line 1')).toBeDefined();
    expect(screen.getByText('n')).toBeDefined();
    expect(screen.getByText('3')).toBeDefined();
    expect(screen.getByText('factorial(3)')).toBeDefined();

    // Trigger forward click
    fireEvent.click(screen.getByLabelText('Step forward'));
    expect(onStepForward).toHaveBeenCalled();

    // Trigger play click
    fireEvent.click(screen.getByLabelText('Play'));
    expect(onPlay).toHaveBeenCalled();
  });
});

describe('CodeEditor Component', () => {
  it('renders code line numbers and highlights active lines', () => {
    const onLineClick = vi.fn();
    const sampleCode = 'x = 10\ny = 20\nz = x + y';

    render(
      <CodeEditor
        code={sampleCode}
        onChange={vi.fn()}
        activeLineNumber={2}
        selectedLineRange={null}
        onLineClick={onLineClick}
      />
    );

    expect(screen.getByText('1')).toBeDefined();
    expect(screen.getByText('2')).toBeDefined();
    expect(screen.getByText('3')).toBeDefined();
    expect(screen.getByText('▶')).toBeDefined();

    // Click line 3 in gutter
    fireEvent.click(screen.getByText('3'));
    expect(onLineClick).toHaveBeenCalledWith(3);
  });
});
