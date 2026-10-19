import React, { useCallback, useMemo, useEffect, useState } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useReactFlow,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  FlowchartNode,
  ArchitectureNode,
  ConceptNode,
  CodeNode,
  SequenceNode,
  ERNode,
  NetworkNode,
  DependencyNode,
} from './CustomNodes';
import { LabeledEdge } from './CustomEdges';
import {
  Plus,
  Trash2,
  Maximize2,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Map,
  Sparkles,
  Layers,
  Database,
} from 'lucide-react';

export default function DiagramCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onEdgeClick,
  onPaneClick,
  selectedNode,
  selectedEdge,
  onAddNode,
  onDeleteSelected,
  onAutoLayout,
}) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const [showMinimap, setShowMinimap] = useState(true);

  const nodeTypes = useMemo(
    () => ({
      flowchart: FlowchartNode,
      process: FlowchartNode,
      architecture: ArchitectureNode,
      concept: ConceptNode,
      concept_map: ConceptNode,
      code: CodeNode,
      code_flow: CodeNode,
      sequence: SequenceNode,
      sequence_diagram: SequenceNode,
      er: ERNode,
      er_diagram: ERNode,
      network: NetworkNode,
      network_topology: NetworkNode,
      dependency: DependencyNode,
      dependency_graph: DependencyNode,
    }),
    []
  );

  const edgeTypes = useMemo(
    () => ({
      labeled: LabeledEdge,
    }),
    []
  );

  // Auto-fit whenever nodes update
  useEffect(() => {
    if (nodes && nodes.length > 0) {
      const timer = setTimeout(() => {
        fitView({ padding: 0.25, duration: 300 });
      }, 80);
      return () => clearTimeout(timer);
    }
  }, [nodes, fitView]);

  const defaultEdgeOptions = useMemo(
    () => ({
      type: 'labeled',
      animated: false,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 14,
        height: 14,
        color: '#94a3b8',
      },
    }),
    []
  );

  return (
    <div className="canvas-container relative w-full h-full flex-1 overflow-hidden">
      {/* Floating Canvas Action Toolbar (Lucidchart-inspired) */}
      <div className="canvas-floating-toolbar">
        <div className="flex items-center gap-1">
          <button
            onClick={() => onAddNode('process')}
            className="canvas-tool-btn"
            title="Add Process Step"
          >
            <Plus size={14} className="text-blue-600" />
            <span>Step</span>
          </button>
          <button
            onClick={() => onAddNode('decision')}
            className="canvas-tool-btn"
            title="Add Decision Diamond"
          >
            <Plus size={14} className="text-amber-600" />
            <span>Decision</span>
          </button>
          <button
            onClick={() => onAddNode('database')}
            className="canvas-tool-btn"
            title="Add Database Node"
          >
            <Database size={13} className="text-sky-600" />
            <span>Data</span>
          </button>
        </div>

        <div className="toolbar-separator" />

        <div className="flex items-center gap-1">
          <button
            onClick={onAutoLayout}
            className="canvas-tool-btn"
            title="Auto-organize Layout"
          >
            <RefreshCw size={13} />
            <span>Auto Layout</span>
          </button>
          <button
            onClick={() => fitView({ padding: 0.25, duration: 250 })}
            className="canvas-tool-btn"
            title="Fit Diagram to View"
          >
            <Maximize2 size={13} />
            <span>Fit</span>
          </button>
          <button
            onClick={() => zoomIn({ duration: 200 })}
            className="canvas-tool-icon-btn"
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => zoomOut({ duration: 200 })}
            className="canvas-tool-icon-btn"
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>
          <button
            onClick={() => setShowMinimap((v) => !v)}
            className={`canvas-tool-icon-btn ${showMinimap ? 'active' : ''}`}
            title="Toggle Minimap"
          >
            <Map size={14} />
          </button>
        </div>

        {(selectedNode || selectedEdge) && (
          <>
            <div className="toolbar-separator" />
            <button
              onClick={onDeleteSelected}
              className="canvas-tool-btn text-rose-600 hover:bg-rose-50 border-rose-200"
              title="Delete Selected Item (Delete/Backspace)"
            >
              <Trash2 size={13} />
              <span>Delete</span>
            </button>
          </>
        )}
      </div>

      {/* Empty State Welcome Card */}
      {(!nodes || nodes.length === 0) && (
        <div className="canvas-empty-state">
          <div className="empty-state-card">
            <div className="empty-state-icon-wrap">
              <Sparkles size={24} className="text-blue-600" />
            </div>
            <h3 className="empty-state-title">Diagram Workspace Ready</h3>
            <p className="empty-state-desc">
              Enter a description in the left panel to automatically generate flowcharts, architectures, sequence diagrams, ER schemas, and dependency graphs.
            </p>
            <div className="empty-state-actions">
              <button
                onClick={() => onAddNode('process')}
                className="btn btn-secondary text-xs"
              >
                <Plus size={14} />
                <span>Add Node Manually</span>
              </button>
            </div>
          </div>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        minZoom={0.2}
        maxZoom={2.5}
        defaultEdgeOptions={defaultEdgeOptions}
      >
        <Controls
          showInteractive={false}
          className="canvas-flow-controls"
        />
        {showMinimap && (
          <MiniMap
            nodeColor={(n) => {
              if (n.type === 'code') return '#334155';
              if (n.type === 'architecture') return '#4f46e5';
              if (n.type === 'er') return '#0284c7';
              if (n.type === 'network') return '#059669';
              return '#2563eb';
            }}
            className="canvas-minimap"
          />
        )}
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#cbd5e1" />
      </ReactFlow>
    </div>
  );
}
