import React, { useState } from 'react';
import {
  Sliders,
  BookOpen,
  ShieldCheck,
  ChevronRight,
  ChevronLeft,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Info,
  Tag,
  Hash,
  ArrowRight,
  GitCommit,
} from 'lucide-react';

export default function RightPanel({
  isCollapsed,
  setIsCollapsed,
  style,
  onResizeStart,
  // Selection
  selectedNode,
  selectedEdge,
  onUpdateNodeLabel,
  onUpdateNodeType,
  onUpdateEdgeLabel,
  onDeleteSelected,
  // Graph metadata
  diagramMetadata,
  validationReport,
  explanationData,
  activeTab,
  setActiveTab,
}) {
  if (isCollapsed) {
    return (
      <aside className="right-panel-collapsed" aria-label="Expand Inspector">
        <button
          onClick={() => setIsCollapsed(false)}
          className="collapse-toggle-btn"
          title="Expand Right Panel"
          aria-label="Expand Right Panel"
        >
          <ChevronLeft size={16} />
        </button>
        <div className="vertical-label-rail">
          <span>PROPERTIES & EXPLANATIONS</span>
        </div>
      </aside>
    );
  }

  return (
    <aside className="right-panel" aria-label="Properties and Diagnostics" style={style}>
      {/* Panel Tab Bar */}
      <div className="panel-tab-bar">
        <button
          onClick={() => setActiveTab('inspector')}
          className={`panel-tab ${activeTab === 'inspector' ? 'active' : ''}`}
        >
          <Sliders size={13} />
          <span>Inspector</span>
        </button>
        <button
          onClick={() => setActiveTab('explanation')}
          className={`panel-tab ${activeTab === 'explanation' ? 'active' : ''}`}
        >
          <BookOpen size={13} />
          <span>Explanation</span>
        </button>
        <button
          onClick={() => setActiveTab('diagnostics')}
          className={`panel-tab ${activeTab === 'diagnostics' ? 'active' : ''}`}
        >
          <ShieldCheck size={13} />
          <span>Diagnostics</span>
          {validationReport?.warnings?.length > 0 && (
            <span className="count-pill">{validationReport.warnings.length}</span>
          )}
        </button>
        <div className="flex-1" />
        <button
          onClick={() => setIsCollapsed(true)}
          className="collapse-toggle-btn mr-1"
          title="Collapse Panel"
          aria-label="Collapse Right Panel"
        >
          <ChevronRight size={15} />
        </button>
      </div>

      <div className="panel-body">
        {/* ================= TAB 1: INSPECTOR ================= */}
        {activeTab === 'inspector' && (
          <div className="space-y-4">
            {/* Case A: A Node is selected */}
            {selectedNode && (
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                  <div className="flex items-center gap-1.5">
                    <span className="badge-pill bg-blue-50 text-blue-700 font-mono text-[11px]">
                      {selectedNode.id}
                    </span>
                    <span className="text-xs font-semibold text-slate-800">Node Properties</span>
                  </div>
                  <button
                    onClick={onDeleteSelected}
                    className="icon-action-btn text-rose-600 hover:bg-rose-50"
                    title="Delete Node"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>

                <div>
                  <label htmlFor="node-label-input" className="section-label">
                    Node Label
                  </label>
                  <input
                    id="node-label-input"
                    type="text"
                    value={selectedNode.data?.label || ''}
                    onChange={(e) => onUpdateNodeLabel(selectedNode.id, e.target.value)}
                    className="lucid-input"
                    placeholder="Enter node label..."
                  />
                </div>

                <div>
                  <label htmlFor="node-type-select" className="section-label">
                    Semantic Role / Type
                  </label>
                  <select
                    id="node-type-select"
                    value={selectedNode.data?.nodeType || 'process'}
                    onChange={(e) => onUpdateNodeType(selectedNode.id, e.target.value)}
                    className="lucid-select"
                  >
                    <option value="process">Process / Action</option>
                    <option value="decision">Decision / Condition</option>
                    <option value="terminal">Terminal / Start / End</option>
                    <option value="service">Microservice / Service</option>
                    <option value="database">Database / Store</option>
                    <option value="gateway">API Gateway / Proxy</option>
                    <option value="cache">Cache / Buffer</option>
                    <option value="client">Client / Frontend</option>
                    <option value="statement">AST Statement</option>
                  </select>
                </div>

                {selectedNode.data?.sourceLocation && (
                  <div className="bg-slate-50 border border-slate-200 rounded p-2 text-xs">
                    <div className="font-medium text-slate-700 mb-1 flex items-center gap-1">
                      <Tag size={12} className="text-blue-500" />
                      <span>AST Source Mapping</span>
                    </div>
                    <div className="text-slate-600 font-mono text-[11px]">
                      Lines: {selectedNode.data.sourceLocation.line_start}
                      {selectedNode.data.sourceLocation.line_end !==
                      selectedNode.data.sourceLocation.line_start
                        ? ` - ${selectedNode.data.sourceLocation.line_end}`
                        : ''}
                    </div>
                  </div>
                )}

                {/* Node coordinates readout */}
                <div className="text-[11px] text-slate-400 font-mono">
                  Pos: ({Math.round(selectedNode.position?.x || 0)}, {Math.round(selectedNode.position?.y || 0)})
                </div>
              </div>
            )}

            {/* Case B: An Edge is selected */}
            {!selectedNode && selectedEdge && (
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                  <div className="flex items-center gap-1.5">
                    <span className="badge-pill bg-indigo-50 text-indigo-700 font-mono text-[11px]">
                      {selectedEdge.id}
                    </span>
                    <span className="text-xs font-semibold text-slate-800">Connection</span>
                  </div>
                  <button
                    onClick={onDeleteSelected}
                    className="icon-action-btn text-rose-600 hover:bg-rose-50"
                    title="Delete Connection"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>

                <div>
                  <label htmlFor="edge-label-input" className="section-label">
                    Relationship Label
                  </label>
                  <input
                    id="edge-label-input"
                    type="text"
                    value={selectedEdge.label || ''}
                    onChange={(e) => onUpdateEdgeLabel(selectedEdge.id, e.target.value)}
                    className="lucid-input"
                    placeholder="e.g. Yes, No, queries, calls..."
                  />
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded p-2 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Source:</span>
                    <span className="font-mono text-slate-800">{selectedEdge.source}</span>
                  </div>
                  <div className="flex items-center justify-center text-slate-400">
                    <ArrowRight size={12} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Target:</span>
                    <span className="font-mono text-slate-800">{selectedEdge.target}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Case C: Nothing selected -> Graph Overview */}
            {!selectedNode && !selectedEdge && (
              <div className="space-y-3">
                <div className="text-xs font-semibold text-slate-800 pb-2 border-b border-slate-200">
                  Document Overview
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="stat-card">
                    <div className="stat-label">Diagram Type</div>
                    <div className="stat-value capitalize text-xs">
                      {diagramMetadata?.type?.replace('_', ' ') || 'None'}
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Layout Direction</div>
                    <div className="stat-value text-xs">
                      {diagramMetadata?.layout_direction || 'TB'}
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Total Nodes</div>
                    <div className="stat-value">{diagramMetadata?.nodeCount || 0}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Total Edges</div>
                    <div className="stat-value">{diagramMetadata?.edgeCount || 0}</div>
                  </div>
                </div>

                <div className="p-3 bg-blue-50/60 border border-blue-100 rounded-md text-xs text-blue-900 leading-relaxed">
                  <div className="font-semibold mb-1 flex items-center gap-1 text-blue-800">
                    <Info size={13} />
                    <span>Interactive Canvas</span>
                  </div>
                  Click any node or relationship line to inspect and edit labels, or drag handles to connect nodes.
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================= TAB 2: EXPLANATION ================= */}
        {activeTab === 'explanation' && (
          <div className="space-y-3">
            <div className="text-xs font-semibold text-slate-800 pb-2 border-b border-slate-200">
              Pedagogical Code Explanation
            </div>

            {explanationData ? (
              <div className="space-y-3 text-xs leading-relaxed text-slate-700">
                {explanationData.summary && (
                  <div className="bg-indigo-50/60 border border-indigo-100 rounded p-2.5">
                    <div className="font-semibold text-indigo-900 mb-1">Concept Summary</div>
                    <p className="text-indigo-950">{explanationData.summary}</p>
                  </div>
                )}

                {explanationData.steps && explanationData.steps.length > 0 && (
                  <div>
                    <div className="font-semibold text-slate-800 mb-1.5">Step-by-Step Logic</div>
                    <ol className="list-decimal pl-4 space-y-1 text-slate-600">
                      {explanationData.steps.map((st, i) => (
                        <li key={i}>{st}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {explanationData.complexity && (
                  <div className="bg-slate-50 border border-slate-200 rounded p-2">
                    <div className="font-semibold text-slate-700">Computational Complexity</div>
                    <div className="font-mono text-[11px] text-slate-600 mt-0.5">
                      {explanationData.complexity}
                    </div>
                  </div>
                )}

                {explanationData.beginner_tips && explanationData.beginner_tips.length > 0 && (
                  <div className="p-2.5 bg-amber-50 border border-amber-200 rounded">
                    <div className="font-semibold text-amber-900 mb-1">Key Takeaways</div>
                    <ul className="list-disc pl-4 space-y-1 text-amber-900 text-[11px]">
                      {explanationData.beginner_tips.map((tip, i) => (
                        <li key={i}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-400 text-xs">
                <BookOpen size={28} className="mx-auto mb-2 text-slate-300" />
                <p>No explanation generated yet.</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  Switch to <b>Explain Code</b> mode and click <b>Explain Code</b> to generate an interactive breakdown.
                </p>
              </div>
            )}
          </div>
        )}

        {/* ================= TAB 3: DIAGNOSTICS ================= */}
        {activeTab === 'diagnostics' && (
          <div className="space-y-3">
            <div className="text-xs font-semibold text-slate-800 pb-2 border-b border-slate-200">
              Graph Integrity & Semantics
            </div>

            {/* Validation Status */}
            <div
              className={`p-2.5 rounded border text-xs ${
                validationReport?.is_valid
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-amber-50 border-amber-200 text-amber-800'
              }`}
            >
              <div className="flex items-center gap-1.5 font-semibold">
                {validationReport?.is_valid ? (
                  <>
                    <CheckCircle2 size={14} className="text-emerald-600" />
                    <span>Schema & Rules Valid</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle size={14} className="text-amber-600" />
                    <span>Validation Flags Detected</span>
                  </>
                )}
              </div>
            </div>

            {/* Warnings list */}
            {validationReport?.warnings && validationReport.warnings.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-slate-700 mb-1.5">
                  Semantic Warnings ({validationReport.warnings.length})
                </div>
                <div className="space-y-1.5">
                  {validationReport.warnings.map((w, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded bg-amber-50/80 border border-amber-200 text-[11px] text-amber-900 leading-relaxed"
                    >
                      {typeof w === 'string'
                        ? w
                        : `${w.code ? `[${w.code}] ` : ''}${w.message || JSON.stringify(w)}`}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Classification confidence */}
            {diagramMetadata?.classification && (
              <div className="bg-slate-50 border border-slate-200 rounded p-2.5 text-xs space-y-1.5">
                <div className="font-semibold text-slate-700 flex items-center justify-between">
                  <span>ML Classification</span>
                  <span className="font-mono text-blue-600">
                    {Math.round((diagramMetadata.classification.confidence || 0) * 100)}%
                  </span>
                </div>
                <div className="text-slate-500 text-[11px]">
                  Model: {diagramMetadata.classification.model || 'TF-IDF Logistic Regression'}
                </div>
                {diagramMetadata.classification.uncertainty_flag && (
                  <div className="text-amber-600 font-medium text-[11px] flex items-center gap-1">
                    <AlertTriangle size={11} />
                    <span>Uncertainty flag: Low confidence classification</span>
                  </div>
                )}
              </div>
            )}

            {/* Tracer Sandbox Configuration */}
            <div className="bg-slate-50 border border-slate-200 rounded p-2.5 text-xs text-slate-600 space-y-1">
              <div className="font-semibold text-slate-700">Subprocess Sandbox Guardrails</div>
              <div>Max Steps: 500</div>
              <div>Timeout: 2.0s wall-clock</div>
              <div>Restricted builtins: sys.settrace sandbox</div>
            </div>
          </div>
        )}
      </div>

      {!isCollapsed && onResizeStart && (
        <div
          className="resize-handle-right"
          onMouseDown={onResizeStart}
          title="Drag to resize inspector"
        />
      )}
    </aside>
  );
}
