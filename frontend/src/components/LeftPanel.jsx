import React, { useState } from 'react';
import {
  Sparkles,
  Play,
  FileCode,
  Network,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  ArrowRight,
  Layers,
  HelpCircle,
  AlertTriangle,
  Flame,
  GitBranch,
  Workflow,
  Boxes,
  Table,
  Share2,
} from 'lucide-react';
import CodeEditor from './CodeEditor';
import { SAMPLE_PROMPTS, SAMPLE_CODE_SNIPPETS } from '../constants/samples';

export default function LeftPanel({
  mode,
  isCollapsed,
  setIsCollapsed,
  style,
  onResizeStart,
  // Text to diagram props
  promptText,
  setPromptText,
  diagramType,
  setDiagramType,
  layoutDirection,
  setLayoutDirection,
  onGenerateDiagram,
  isGenerating,
  // Explain code props
  code,
  setCode,
  activeLineNumber,
  selectedLineRange,
  onLineClick,
  codeLanguage,
  codeViewMode,
  setCodeViewMode,
  onAnalyzeCode,
  isAnalyzing,
  onTraceCode,
  isTracing,
  onExplainCode,
  isExplaining,
  // Error feedback
  errorMessage,
  onClearError,
}) {
  const [selectedPromptSample, setSelectedPromptSample] = useState('');
  const [selectedCodeSample, setSelectedCodeSample] = useState('');

  const handleSelectPromptSample = (sample) => {
    setSelectedPromptSample(sample.id);
    setPromptText(sample.text);
    if (sample.type) {
      setDiagramType(sample.type);
    }
  };

  const handleSelectCodeSample = (sample) => {
    setSelectedCodeSample(sample.id);
    setCode(sample.code);
  };

  const getTemplateIcon = (type) => {
    switch (type) {
      case 'architecture':
        return <Boxes size={12} className="text-indigo-500 shrink-0" />;
      case 'concept_map':
        return <Share2 size={12} className="text-purple-500 shrink-0" />;
      case 'sequence_diagram':
        return <ArrowRight size={12} className="text-blue-500 shrink-0" />;
      case 'er_diagram':
        return <Table size={12} className="text-sky-500 shrink-0" />;
      case 'network_topology':
        return <Network size={12} className="text-emerald-500 shrink-0" />;
      case 'dependency_graph':
        return <GitBranch size={12} className="text-amber-500 shrink-0" />;
      default:
        return <Workflow size={12} className="text-blue-500 shrink-0" />;
    }
  };

  if (isCollapsed) {
    return (
      <aside className="left-panel-collapsed" aria-label="Expand Controls">
        <button
          onClick={() => setIsCollapsed(false)}
          className="collapse-toggle-btn"
          title="Expand Left Panel"
          aria-label="Expand Left Panel"
        >
          <ChevronRight size={16} />
        </button>
        <div className="vertical-label-rail">
          <span>{mode === 'text' ? 'TEXT TO DIAGRAM' : 'EXPLAIN CODE'}</span>
        </div>
      </aside>
    );
  }

  return (
    <aside className="left-panel" aria-label="Editor Controls" style={style}>
      <div className="panel-header">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            {mode === 'text' ? (
              <Sparkles size={16} className="text-blue-600" />
            ) : (
              <FileCode size={16} className="text-indigo-600" />
            )}
            <h2 className="panel-title">
              {mode === 'text' ? 'Text to Diagram' : 'Code Analysis & Trace'}
            </h2>
          </div>
          <button
            onClick={() => setIsCollapsed(true)}
            className="collapse-toggle-btn"
            title="Collapse Panel (Maximize Canvas)"
            aria-label="Collapse Left Panel"
          >
            <ChevronLeft size={16} />
          </button>
        </div>
      </div>

      <div className="panel-body">
        {/* Error notification banner */}
        {errorMessage && (
          <div className="error-banner">
            <div className="flex items-start gap-2">
              <AlertTriangle size={15} className="text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1 text-xs text-rose-800 leading-relaxed font-medium">
                {errorMessage}
              </div>
              <button
                onClick={onClearError}
                className="text-rose-500 hover:text-rose-800 text-xs font-bold"
                aria-label="Dismiss error"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* ---------------- MODE: TEXT TO DIAGRAM ---------------- */}
        {mode === 'text' && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="prompt-input" className="section-label">
                  Natural Language Prompt
                </label>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400 font-mono">
                    {promptText?.length || 0} / 10,000
                  </span>
                  {promptText && (
                    <button
                      onClick={() => setPromptText('')}
                      className="text-xs text-slate-400 hover:text-slate-600"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
              <textarea
                id="prompt-input"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                placeholder="Describe your workflow, architecture, system process, sequence, or schema..."
                rows={4}
                className="lucid-textarea"
              />
            </div>

            {/* Diagram Type Selector */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="diagram-type-select" className="section-label">
                  Diagram Family
                </label>
                <select
                  id="diagram-type-select"
                  value={diagramType}
                  onChange={(e) => setDiagramType(e.target.value)}
                  className="lucid-select"
                >
                  <option value="">Auto-Detect (ML Model)</option>
                  <option value="flowchart">Flowchart</option>
                  <option value="architecture">Software Architecture</option>
                  <option value="concept_map">Concept Map</option>
                  <option value="sequence_diagram">Sequence Diagram</option>
                  <option value="er_diagram">Entity-Relationship</option>
                  <option value="network_topology">Network Topology</option>
                  <option value="dependency_graph">Dependency / CI-CD</option>
                </select>
              </div>

              <div>
                <label htmlFor="layout-direction-select" className="section-label">
                  Layout Flow
                </label>
                <select
                  id="layout-direction-select"
                  value={layoutDirection}
                  onChange={(e) => setLayoutDirection(e.target.value)}
                  className="lucid-select"
                >
                  <option value="TB">Top to Bottom (↓ TB)</option>
                  <option value="LR">Left to Right (→ LR)</option>
                </select>
              </div>
            </div>

            {/* Quick Sample Prompts */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="section-label">Sample Templates</span>
                <span className="text-[10px] text-slate-400">Click to load</span>
              </div>
              <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                {SAMPLE_PROMPTS.map((sample) => (
                  <button
                    key={sample.id}
                    onClick={() => handleSelectPromptSample(sample)}
                    className={`sample-chip-btn ${selectedPromptSample === sample.id ? 'active' : ''}`}
                  >
                    <div className="flex items-center gap-1.5 truncate">
                      {getTemplateIcon(sample.type)}
                      <span className="font-medium truncate">{sample.title}</span>
                    </div>
                    <span className="sample-badge">{sample.type.replace('_', ' ')}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Action CTA */}
            <div className="pt-2">
              <button
                id="generate-btn"
                onClick={onGenerateDiagram}
                disabled={isGenerating}
                className="btn-primary w-full"
              >
                {isGenerating ? (
                  <>
                    <RotateCcw size={14} className="animate-spin" />
                    <span>Analyzing & Synthesizing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={14} />
                    <span>Generate Diagram</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ---------------- MODE: EXPLAIN CODE ---------------- */}
        {mode === 'code' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="badge-pill bg-emerald-50 text-emerald-700 border-emerald-200">
                  {codeLanguage.toUpperCase()} 3.10+
                </span>
                <span className="text-[11px] text-slate-500">AST & Tracer</span>
              </div>

              {/* View mode toggle */}
              <div className="inline-flex rounded-md border border-slate-200 bg-slate-50 p-0.5 text-xs">
                <button
                  onClick={() => setCodeViewMode('cfg')}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                    codeViewMode === 'cfg'
                      ? 'bg-white text-blue-600 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                  title="Control Flow Graph"
                >
                  CFG
                </button>
                <button
                  onClick={() => setCodeViewMode('callgraph')}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                    codeViewMode === 'callgraph'
                      ? 'bg-white text-blue-600 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                  title="Function Call Graph"
                >
                  Calls
                </button>
              </div>
            </div>

            {/* Code Samples Dropdown */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label htmlFor="code-sample-select" className="section-label">
                  Code Snippet
                </label>
                <span className="text-[10px] text-slate-400">Pure Python</span>
              </div>
              <select
                id="code-sample-select"
                value={selectedCodeSample}
                onChange={(e) => {
                  const sample = SAMPLE_CODE_SNIPPETS.find((s) => s.id === e.target.value);
                  if (sample) handleSelectCodeSample(sample);
                }}
                className="lucid-select mb-2"
              >
                <option value="">Select a Python sample...</option>
                {SAMPLE_CODE_SNIPPETS.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title}
                  </option>
                ))}
              </select>

              {/* Custom Gutter Code Editor */}
              <CodeEditor
                code={code}
                onChange={setCode}
                activeLineNumber={activeLineNumber}
                selectedLineRange={selectedLineRange}
                onLineClick={onLineClick}
              />
            </div>

            {/* Code Actions Grid */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                id="analyze-code-btn"
                onClick={onAnalyzeCode}
                disabled={isAnalyzing || !code.trim()}
                className="btn-secondary"
                title="Generate AST Control Flow Graph"
              >
                {isAnalyzing ? (
                  <RotateCcw size={13} className="animate-spin" />
                ) : (
                  <Network size={13} />
                )}
                <span>{codeViewMode === 'cfg' ? 'Analyze CFG' : 'Call Graph'}</span>
              </button>

              <button
                id="explain-code-btn"
                onClick={onExplainCode}
                disabled={isExplaining || !code.trim()}
                className="btn-secondary"
                title="Get Pedagogical Explanation"
              >
                {isExplaining ? (
                  <RotateCcw size={13} className="animate-spin" />
                ) : (
                  <BookOpen size={13} />
                )}
                <span>Explain Code</span>
              </button>
            </div>

            {/* Run Execution Trace CTA */}
            <button
              id="trace-code-btn"
              onClick={onTraceCode}
              disabled={isTracing || !code.trim()}
              className="btn-primary w-full"
              title="Execute in Subprocess Sandbox & Capture Variable States"
            >
              {isTracing ? (
                <>
                  <RotateCcw size={14} className="animate-spin" />
                  <span>Executing in Sandbox...</span>
                </>
              ) : (
                <>
                  <Play size={14} fill="currentColor" />
                  <span>Run Sandbox Trace</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {!isCollapsed && onResizeStart && (
        <div
          className="resize-handle-left"
          onMouseDown={onResizeStart}
          title="Drag to resize panel"
        />
      )}
    </aside>
  );
}
