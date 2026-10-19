import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ReactFlowProvider, applyNodeChanges, applyEdgeChanges, addEdge } from '@xyflow/react';
import { toPng, toSvg } from 'html-to-image';

import TopNav from './components/TopNav';
import LeftPanel from './components/LeftPanel';
import RightPanel from './components/RightPanel';
import DiagramCanvas from './components/Canvas/DiagramCanvas';
import PlaybackBar from './components/PlaybackBar';
import { api } from './api/client';
import { SAMPLE_PROMPTS, SAMPLE_CODE_SNIPPETS } from './constants/samples';

// Helper to convert backend diagram graph to React Flow elements
function transformBackendGraphToFlow(graph, activeLine = null) {
  if (!graph || !Array.isArray(graph.nodes)) {
    return { nodes: [], edges: [] };
  }

  const diagramType = (graph.diagram_type || 'flowchart').toLowerCase();

  const flowNodes = graph.nodes.map((n, idx) => {
    let customType = 'flowchart';
    const semanticType = (n.type || '').toLowerCase();
    if (semanticType === 'code' || (n.source_location && n.source_location.line_start)) {
      customType = 'code';
    } else if (
      diagramType === 'architecture' ||
      ['service', 'database', 'gateway', 'client', 'cache'].includes(semanticType)
    ) {
      customType = 'architecture';
    } else if (diagramType === 'concept_map') {
      customType = 'concept';
    } else if (diagramType === 'sequence_diagram' || diagramType === 'sequence') {
      customType = 'sequence';
    } else if (diagramType === 'er_diagram' || diagramType === 'er') {
      customType = 'er';
    } else if (diagramType === 'network_topology' || diagramType === 'network') {
      customType = 'network';
    } else if (diagramType === 'dependency_graph' || diagramType === 'dependency') {
      customType = 'dependency';
    }

    const isLineMatch =
      activeLine &&
      n.source_location &&
      n.source_location.line_start <= activeLine &&
      n.source_location.line_end >= activeLine;

    const posX = typeof n.position?.x === 'number' ? n.position.x : idx * 180 + 50;
    const posY = typeof n.position?.y === 'number' ? n.position.y : idx * 100 + 50;

    return {
      id: String(n.id),
      type: customType,
      position: { x: posX, y: posY },
      data: {
        label: n.label || n.id,
        nodeType: n.type || 'process',
        attributes: n.attributes || {},
        sourceLocation: n.source_location || null,
        executionState: n.execution_state || null,
        isActiveStep: !!isLineMatch,
      },
    };
  });

  const nodeIds = new Set(flowNodes.map((n) => n.id));
  const rawEdges = Array.isArray(graph.edges)
    ? graph.edges
    : Array.isArray(graph.relationships)
    ? graph.relationships
    : [];

  const flowEdges = rawEdges
    .filter((r) => r && r.source && r.target && nodeIds.has(String(r.source)) && nodeIds.has(String(r.target)))
    .map((r, idx) => ({
      id: r.id ? String(r.id) : `edge-${r.source}-${r.target}-${idx}`,
      source: String(r.source),
      target: String(r.target),
      label: r.label || (r.edge_type && r.edge_type !== 'flow' && r.edge_type !== 'sequence' && r.edge_type !== 'default' ? r.edge_type : ''),
      type: 'labeled',
      data: {
        relType: r.edge_type || r.type || 'flow',
        bidirectional: r.directed === false || r.bidirectional === true,
      },
    }));

  return { nodes: flowNodes, edges: flowEdges };
}

// Convert React Flow back to Generalized Diagram Graph
function transformFlowToBackendGraph(nodes, edges, diagramType = 'flowchart', layoutDir = 'TB') {
  const transformedNodes = nodes.map((n) => ({
    id: n.id,
    label: n.data.label || n.id,
    type: n.data.nodeType || 'process',
    position: {
      x: Math.round(n.position.x),
      y: Math.round(n.position.y),
    },
    source_location: n.data.sourceLocation || null,
    execution_state: n.data.executionState || null,
    attributes: n.data.attributes || {},
  }));

  const transformedEdges = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label || '',
    edge_type: e.data?.relType || 'flow',
    type: e.data?.relType || 'flow',
    directed: !e.data?.bidirectional,
  }));

  return {
    id: `diagram-${Date.now()}`,
    diagram_type: diagramType,
    layout_direction: layoutDir,
    nodes: transformedNodes,
    edges: transformedEdges,
    relationships: transformedEdges,
  };
}

export default function App() {
  // Top level mode & metadata
  const [mode, setMode] = useState('text'); // 'text' | 'code'
  const [title, setTitle] = useState('AI Diagram Canvas');
  const [backendOnline, setBackendOnline] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  // Panel collapse & resize states
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [activeRightTab, setActiveRightTab] = useState('inspector');
  const [leftWidth, setLeftWidth] = useState(360);
  const [rightWidth, setRightWidth] = useState(330);
  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);

  const handleLeftResizeStart = useCallback((e) => {
    e.preventDefault();
    setIsResizingLeft(true);
  }, []);

  const handleRightResizeStart = useCallback((e) => {
    e.preventDefault();
    setIsResizingRight(true);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizingLeft) {
        const newWidth = Math.max(280, Math.min(e.clientX, 600));
        setLeftWidth(newWidth);
      }
      if (isResizingRight) {
        const newWidth = Math.max(260, Math.min(window.innerWidth - e.clientX, 550));
        setRightWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizingLeft(false);
      setIsResizingRight(false);
    };

    if (isResizingLeft || isResizingRight) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizingLeft, isResizingRight]);

  // Text Mode state
  const [promptText, setPromptText] = useState(SAMPLE_PROMPTS[0].text);
  const [diagramType, setDiagramType] = useState('flowchart');
  const [layoutDirection, setLayoutDirection] = useState('TB');
  const [isGenerating, setIsGenerating] = useState(false);

  // Code Mode state
  const [code, setCode] = useState(SAMPLE_CODE_SNIPPETS[0].code);
  const [codeLanguage, setCodeLanguage] = useState('python');
  const [codeViewMode, setCodeViewMode] = useState('cfg');
  const [activeLineNumber, setActiveLineNumber] = useState(null);
  const [selectedLineRange, setSelectedLineRange] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isTracing, setIsTracing] = useState(false);
  const [isExplaining, setIsExplaining] = useState(false);

  // Stepper & Playback state
  const [traceEvents, setTraceEvents] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const playTimerRef = useRef(null);

  // Canvas graph state
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);

  // Metadata & Inspection
  const [diagramMetadata, setDiagramMetadata] = useState(null);
  const [validationReport, setValidationReport] = useState(null);
  const [explanationData, setExplanationData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  // Undo / Redo history
  const [history, setHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const pushHistory = useCallback(
    (newNodes, newEdges) => {
      setHistory((prev) => {
        const nextHist = prev.slice(0, historyIndex + 1);
        nextHist.push({ nodes: newNodes, edges: newEdges });
        return nextHist.slice(-25); // cap at 25 undo steps
      });
      setHistoryIndex((prev) => Math.min(prev + 1, 24));
      setIsDirty(true);
    },
    [historyIndex]
  );

  // Probe backend health on mount
  useEffect(() => {
    let mounted = true;
    api
      .getHealth()
      .then(() => {
        if (mounted) setBackendOnline(true);
      })
      .catch(() => {
        if (mounted) setBackendOnline(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Synchronize playback active line with canvas node highlighting
  useEffect(() => {
    if (traceEvents.length > 0 && traceEvents[currentStep]) {
      const lineNo = traceEvents[currentStep].line_number;
      setActiveLineNumber(lineNo);

      // Highlight corresponding node
      setNodes((currentNodes) =>
        currentNodes.map((node) => {
          const loc = node.data.sourceLocation;
          const match = loc && loc.line_start <= lineNo && loc.line_end >= lineNo;
          return {
            ...node,
            data: {
              ...node.data,
              isActiveStep: !!match,
              executionState: match ? { variables: traceEvents[currentStep].variables } : null,
            },
          };
        })
      );
    }
  }, [currentStep, traceEvents]);

  // Stepper Interval Loop
  useEffect(() => {
    if (isPlaying && traceEvents.length > 0) {
      const intervalMs = Math.round(1000 / playbackSpeed);
      playTimerRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= traceEvents.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, intervalMs);
    } else {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    }
    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, traceEvents.length, playbackSpeed]);

  // Node & Edge changes handlers
  const onNodesChange = useCallback(
    (changes) => {
      setNodes((nds) => {
        const updated = applyNodeChanges(changes, nds);
        return updated;
      });
      setIsDirty(true);
    },
    []
  );

  const onEdgesChange = useCallback(
    (changes) => {
      setEdges((eds) => {
        const updated = applyEdgeChanges(changes, eds);
        return updated;
      });
      setIsDirty(true);
    },
    []
  );

  const onConnect = useCallback(
    (params) => {
      const newEdge = {
        ...params,
        type: 'labeled',
        id: `edge-${params.source}-${params.target}-${Date.now()}`,
        data: { relType: 'sequence' },
      };
      setEdges((eds) => {
        const updated = addEdge(newEdge, eds);
        pushHistory(nodes, updated);
        return updated;
      });
    },
    [nodes, pushHistory]
  );

  // Selection handlers
  const onNodeClick = useCallback(
    (_, node) => {
      setSelectedNode(node);
      setSelectedEdge(null);
      if (node.data.sourceLocation) {
        setSelectedLineRange({
          start: node.data.sourceLocation.line_start,
          end: node.data.sourceLocation.line_end,
        });
      }
      setActiveRightTab('inspector');
    },
    []
  );

  const onEdgeClick = useCallback((_, edge) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
    setActiveRightTab('inspector');
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
    setSelectedLineRange(null);
  }, []);

  // Update properties from Inspector
  const onUpdateNodeLabel = useCallback(
    (nodeId, newLabel) => {
      setNodes((nds) => {
        const updated = nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, label: newLabel } } : n
        );
        if (selectedNode && selectedNode.id === nodeId) {
          setSelectedNode((prev) => ({ ...prev, data: { ...prev.data, label: newLabel } }));
        }
        return updated;
      });
      setIsDirty(true);
    },
    [selectedNode]
  );

  const onUpdateNodeType = useCallback(
    (nodeId, newType) => {
      setNodes((nds) => {
        const updated = nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, nodeType: newType } } : n
        );
        if (selectedNode && selectedNode.id === nodeId) {
          setSelectedNode((prev) => ({ ...prev, data: { ...prev.data, nodeType: newType } }));
        }
        return updated;
      });
      setIsDirty(true);
    },
    [selectedNode]
  );

  const onUpdateEdgeLabel = useCallback(
    (edgeId, newLabel) => {
      setEdges((eds) => {
        const updated = eds.map((e) => (e.id === edgeId ? { ...e, label: newLabel } : e));
        if (selectedEdge && selectedEdge.id === edgeId) {
          setSelectedEdge((prev) => ({ ...prev, label: newLabel }));
        }
        return updated;
      });
      setIsDirty(true);
    },
    [selectedEdge]
  );

  // Add & Delete Canvas Nodes/Edges
  const handleAddNode = useCallback(
    (type = 'process') => {
      const newId = `node_${nodes.length + 1}`;
      let customType = 'flowchart';
      if (type === 'database') customType = 'architecture';
      else if (diagramType === 'architecture') customType = 'architecture';
      else if (diagramType === 'concept_map') customType = 'concept';
      else if (diagramType === 'er_diagram') customType = 'er';
      else if (diagramType === 'sequence_diagram') customType = 'sequence';
      else if (diagramType === 'network_topology') customType = 'network';
      else if (diagramType === 'dependency_graph') customType = 'dependency';

      const newNode = {
        id: newId,
        type: customType,
        position: {
          x: 200 + (nodes.length % 5) * 40,
          y: 150 + (nodes.length % 5) * 40,
        },
        data: {
          label: `New ${type.charAt(0).toUpperCase() + type.slice(1)}`,
          nodeType: type,
          attributes: {},
        },
      };
      const updatedNodes = [...nodes, newNode];
      setNodes(updatedNodes);
      setSelectedNode(newNode);
      setDiagramMetadata((prev) => ({
        type: prev?.type || diagramType || 'flowchart',
        layout_direction: prev?.layout_direction || layoutDirection || 'TB',
        ...prev,
        nodeCount: updatedNodes.length,
        edgeCount: edges.length,
      }));
      pushHistory(updatedNodes, edges);
    },
    [nodes, edges, diagramType, layoutDirection, pushHistory]
  );

  const handleDeleteSelected = useCallback(() => {
    if (selectedNode) {
      const updatedNodes = nodes.filter((n) => n.id !== selectedNode.id);
      const updatedEdges = edges.filter(
        (e) => e.source !== selectedNode.id && e.target !== selectedNode.id
      );
      setNodes(updatedNodes);
      setEdges(updatedEdges);
      setSelectedNode(null);
      setDiagramMetadata((prev) =>
        prev
          ? { ...prev, nodeCount: updatedNodes.length, edgeCount: updatedEdges.length }
          : null
      );
      pushHistory(updatedNodes, updatedEdges);
    } else if (selectedEdge) {
      const updatedEdges = edges.filter((e) => e.id !== selectedEdge.id);
      setEdges(updatedEdges);
      setSelectedEdge(null);
      setDiagramMetadata((prev) =>
        prev ? { ...prev, nodeCount: nodes.length, edgeCount: updatedEdges.length } : null
      );
      pushHistory(nodes, updatedEdges);
    }
  }, [selectedNode, selectedEdge, nodes, edges, pushHistory]);

  // Undo / Redo
  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const prevSnap = history[historyIndex - 1];
      setNodes(prevSnap.nodes);
      setEdges(prevSnap.edges);
      setHistoryIndex(historyIndex - 1);
    }
  }, [history, historyIndex]);

  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const nextSnap = history[historyIndex + 1];
      setNodes(nextSnap.nodes);
      setEdges(nextSnap.edges);
      setHistoryIndex(historyIndex + 1);
    }
  }, [history, historyIndex]);

  // Keyboard shortcut listener (Delete / Backspace / Ctrl+Z)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'Delete' || e.key === 'Backspace') {
        handleDeleteSelected();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        if (e.shiftKey) {
          handleRedo();
        } else {
          handleUndo();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleDeleteSelected, handleUndo, handleRedo]);

  // Auto Layout action
  const handleAutoLayout = useCallback(() => {
    // Hierarchical top-down distribution
    const levelSpacing = 110;
    const colSpacing = 200;
    const positioned = nodes.map((n, i) => ({
      ...n,
      position: {
        x: 100 + (i % 3) * colSpacing,
        y: 80 + Math.floor(i / 3) * levelSpacing,
      },
    }));
    setNodes(positioned);
    pushHistory(positioned, edges);
  }, [nodes, edges, pushHistory]);

  // API Call: Text to Diagram Generation
  const handleGenerateDiagram = async () => {
    // 1. Validate prompt input
    const trimmedPrompt = (promptText || '').trim();
    if (!trimmedPrompt) {
      setErrorMessage('Please enter a natural language prompt describing your workflow or architecture.');
      return;
    }
    if (trimmedPrompt.length < 5) {
      setErrorMessage('Prompt must be at least 5 characters long.');
      return;
    }

    // 2. Validate diagram family & layout options
    const validTypes = [
      '',
      'flowchart',
      'architecture',
      'concept_map',
      'sequence_diagram',
      'er_diagram',
      'network_topology',
      'dependency_graph',
    ];
    if (diagramType && !validTypes.includes(diagramType)) {
      setErrorMessage(`Invalid diagram type: "${diagramType}". Please select a supported type.`);
      return;
    }

    const validDirections = ['TB', 'LR'];
    if (layoutDirection && !validDirections.includes(layoutDirection)) {
      setErrorMessage(`Invalid layout direction: "${layoutDirection}". Supported directions are TB or LR.`);
      return;
    }

    // 3. Prevent duplicate submissions & set loading state
    if (isGenerating) return;
    setIsGenerating(true);
    setErrorMessage('');

    try {
      // 4. Call real FastAPI endpoint
      const resp = await api.generateDiagram(
        trimmedPrompt,
        diagramType || null,
        layoutDirection || 'TB'
      );

      // 6. Parse response correctly
      const graph = resp?.diagram;
      if (!graph || !Array.isArray(graph.nodes)) {
        throw new Error('Backend returned an invalid diagram response (missing nodes array).');
      }

      // 7. Convert to React Flow format
      const { nodes: flowNodes, edges: flowEdges } = transformBackendGraphToFlow(graph);

      // 8. Update diagram state
      setNodes(flowNodes);
      setEdges(flowEdges);

      const effectiveType = resp.diagram_type || graph.diagram_type || diagramType || 'flowchart';
      const effectiveDirection = graph.layout_config?.direction || layoutDirection || 'TB';

      // 9. Update inspector node and edge counts
      setDiagramMetadata({
        type: effectiveType,
        layout_direction: effectiveDirection,
        nodeCount: flowNodes.length,
        edgeCount: flowEdges.length,
        confidence: resp.confidence ?? null,
        execution_time_ms: resp.execution_time_ms ?? null,
        classification: resp.classification || {
          predicted_type: effectiveType,
          confidence: resp.confidence ?? null,
        },
      });

      // 10. Display backend warnings if any
      const backendWarnings = resp.warnings || graph.warnings || [];
      setValidationReport(
        resp.validation || {
          is_valid: true,
          warnings: backendWarnings,
          diagram_type: effectiveType,
        }
      );

      setSelectedNode(null);
      setSelectedEdge(null);
      setHistory([{ nodes: flowNodes, edges: flowEdges }]);
      setHistoryIndex(0);
      setIsDirty(false);
      setBackendOnline(true);

      // Fit the generated graph into view
      setTimeout(() => {
        handleFitView();
      }, 100);
    } catch (err) {
      // 5. Handle non-success and network errors without swallowing
      setErrorMessage(err.message || 'Diagram generation failed.');
      if (err.code === 'NETWORK_ERROR') setBackendOnline(false);
    } finally {
      setIsGenerating(false);
    }
  };

  // API Call: Explain Code AST Analysis
  const handleAnalyzeCode = async () => {
    if (!code.trim()) return;
    setIsAnalyzing(true);
    setErrorMessage('');

    try {
      const resp = await api.analyzeCode(code, codeLanguage, codeViewMode, layoutDirection);
      const graph = resp.diagram;
      const { nodes: flowNodes, edges: flowEdges } = transformBackendGraphToFlow(graph);

      setNodes(flowNodes);
      setEdges(flowEdges);
      setDiagramMetadata({
        type: graph.diagram_type || 'flowchart',
        layout_direction: layoutDirection,
        nodeCount: flowNodes.length,
        edgeCount: flowEdges.length,
        analysisMode: codeViewMode,
      });
      setValidationReport(resp.validation || { is_valid: true, warnings: [] });
      setHistory([{ nodes: flowNodes, edges: flowEdges }]);
      setHistoryIndex(0);
      setIsDirty(false);
      setBackendOnline(true);
    } catch (err) {
      setErrorMessage(err.message || 'Code analysis failed.');
      if (err.code === 'NETWORK_ERROR') setBackendOnline(false);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // API Call: Pedagogical Explanation
  const handleExplainCode = async () => {
    if (!code.trim()) return;
    setIsExplaining(true);
    setErrorMessage('');

    try {
      const resp = await api.explainCode(
        code,
        codeLanguage,
        activeLineNumber,
        selectedNode?.id || null
      );
      setExplanationData(resp.explanation);
      setActiveRightTab('explanation');
      setRightCollapsed(false);
      setBackendOnline(true);
    } catch (err) {
      setErrorMessage(err.message || 'Code explanation failed.');
      if (err.code === 'NETWORK_ERROR') setBackendOnline(false);
    } finally {
      setIsExplaining(false);
    }
  };

  // API Call: Execution Sandbox Tracer
  const handleTraceCode = async () => {
    if (!code.trim()) return;
    setIsTracing(true);
    setErrorMessage('');

    try {
      const traceResp = await api.traceCode(code, codeLanguage);
      const events = traceResp?.trace?.events || traceResp?.events || [];
      if (events.length > 0) {
        setTraceEvents(events);
        setCurrentStep(0);
        setIsPlaying(true);
      } else {
        setErrorMessage('Trace returned 0 execution events. Ensure code is runnable.');
      }

      // Also ensure CFG diagram is present if not already generated
      const diagram = traceResp?.diagram;
      if (diagram && Array.isArray(diagram.nodes) && diagram.nodes.length > 0) {
        const { nodes: flowNodes, edges: flowEdges } = transformBackendGraphToFlow(
          diagram,
          events[0]?.line_number
        );
        setNodes(flowNodes);
        setEdges(flowEdges);
      } else if (nodes.length === 0) {
        const analyzeResp = await api.analyzeCode(code, codeLanguage, 'cfg', layoutDirection);
        const { nodes: flowNodes, edges: flowEdges } = transformBackendGraphToFlow(
          analyzeResp.diagram,
          events[0]?.line_number
        );
        setNodes(flowNodes);
        setEdges(flowEdges);
      }
      setBackendOnline(true);
    } catch (err) {
      setErrorMessage(err.message || 'Sandbox trace failed.');
      if (err.code === 'NETWORK_ERROR') setBackendOnline(false);
    } finally {
      setIsTracing(false);
    }
  };

  // Export handlers
  const handleExport = async (format) => {
    const canvasEl = document.querySelector('.react-flow__viewport');
    if (!canvasEl) return;

    if (format === 'json') {
      const exportData = transformFlowToBackendGraph(
        nodes,
        edges,
        diagramMetadata?.type || diagramType,
        layoutDirection
      );
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.toLowerCase().replace(/\s+/g, '_')}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setIsDirty(false);
    } else if (format === 'png') {
      try {
        const dataUrl = await toPng(canvasEl, { backgroundColor: '#f8fafc' });
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = `${title.toLowerCase().replace(/\s+/g, '_')}.png`;
        a.click();
      } catch (err) {
        setErrorMessage('PNG export failed: ' + err.message);
      }
    } else if (format === 'svg') {
      try {
        const dataUrl = await toSvg(canvasEl, { backgroundColor: '#f8fafc' });
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = `${title.toLowerCase().replace(/\s+/g, '_')}.svg`;
        a.click();
      } catch (err) {
        setErrorMessage('SVG export failed: ' + err.message);
      }
    }
  };

  // Import JSON diagram handler
  const handleImport = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const importedJson = JSON.parse(event.target.result);
        const { nodes: flowNodes, edges: flowEdges } = transformBackendGraphToFlow(importedJson);

        setNodes(flowNodes);
        setEdges(flowEdges);
        setDiagramMetadata({
          type: importedJson.diagram_type || 'flowchart',
          layout_direction: importedJson.layout_direction || 'TB',
          nodeCount: flowNodes.length,
          edgeCount: flowEdges.length,
        });

        // Validate with backend if connected
        try {
          const valResp = await api.validateDiagram(importedJson);
          setValidationReport(valResp.validation);
        } catch {
          // ignore validation error if offline
        }

        pushHistory(flowNodes, flowEdges);
        setIsDirty(false);
      } catch (err) {
        setErrorMessage('Invalid diagram JSON format: ' + err.message);
      }
    };
    reader.readAsText(file);
    e.target.value = ''; // reset file input
  };

  // Fit View callback trigger
  const handleFitView = () => {
    const fitBtn = document.querySelector('.react-flow__controls-fitview');
    if (fitBtn) fitBtn.click();
  };

  return (
    <div className="app-container flex flex-col w-screen h-screen overflow-hidden">
      {/* Top Application Bar */}
      <TopNav
        mode={mode}
        setMode={setMode}
        title={title}
        setTitle={setTitle}
        isDirty={isDirty}
        onExport={handleExport}
        onImport={handleImport}
        onUndo={handleUndo}
        onRedo={handleRedo}
        canUndo={historyIndex > 0}
        canRedo={historyIndex < history.length - 1}
        onFitView={handleFitView}
        backendOnline={backendOnline}
      />

      {/* Main Workspace Layout */}
      <main className="main-workspace">
        {/* Left Control Panel */}
        <LeftPanel
          style={{ width: leftCollapsed ? 38 : `${leftWidth}px` }}
          onResizeStart={handleLeftResizeStart}
          mode={mode}
          isCollapsed={leftCollapsed}
          setIsCollapsed={setLeftCollapsed}
          promptText={promptText}
          setPromptText={setPromptText}
          diagramType={diagramType}
          setDiagramType={setDiagramType}
          layoutDirection={layoutDirection}
          setLayoutDirection={setLayoutDirection}
          onGenerateDiagram={handleGenerateDiagram}
          isGenerating={isGenerating}
          code={code}
          setCode={setCode}
          activeLineNumber={activeLineNumber}
          selectedLineRange={selectedLineRange}
          onLineClick={(line) => {
            setActiveLineNumber(line);
            setSelectedLineRange({ start: line, end: line });
          }}
          codeLanguage={codeLanguage}
          codeViewMode={codeViewMode}
          setCodeViewMode={setCodeViewMode}
          onAnalyzeCode={handleAnalyzeCode}
          isAnalyzing={isAnalyzing}
          onTraceCode={handleTraceCode}
          isTracing={isTracing}
          onExplainCode={handleExplainCode}
          isExplaining={isExplaining}
          errorMessage={errorMessage}
          onClearError={() => setErrorMessage('')}
        />

        {/* Central Canvas */}
        <section className="canvas-wrapper" aria-label="Diagram Canvas">
          <ReactFlowProvider>
            <DiagramCanvas
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              onEdgeClick={onEdgeClick}
              onPaneClick={onPaneClick}
              selectedNode={selectedNode}
              selectedEdge={selectedEdge}
              onAddNode={handleAddNode}
              onDeleteSelected={handleDeleteSelected}
              onAutoLayout={handleAutoLayout}
            />
          </ReactFlowProvider>

          {/* Bottom Execution Trace Stepper (Docked when traces exist in Code mode) */}
          {mode === 'code' && traceEvents.length > 0 && (
            <PlaybackBar
              traceEvents={traceEvents}
              currentStep={currentStep}
              isPlaying={isPlaying}
              playbackSpeed={playbackSpeed}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onStepBack={() => setCurrentStep((s) => Math.max(0, s - 1))}
              onStepForward={() => setCurrentStep((s) => Math.min(traceEvents.length - 1, s + 1))}
              onReset={() => {
                setCurrentStep(0);
                setIsPlaying(false);
              }}
              onSeek={(s) => setCurrentStep(s)}
              onSpeedChange={(sp) => setPlaybackSpeed(sp)}
              onClose={() => {
                setTraceEvents([]);
                setIsPlaying(false);
              }}
            />
          )}
        </section>

        {/* Right Properties & Explanation Panel */}
        <RightPanel
          style={{ width: rightCollapsed ? 38 : `${rightWidth}px` }}
          onResizeStart={handleRightResizeStart}
          isCollapsed={rightCollapsed}
          setIsCollapsed={setRightCollapsed}
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          onUpdateNodeLabel={onUpdateNodeLabel}
          onUpdateNodeType={onUpdateNodeType}
          onUpdateEdgeLabel={onUpdateEdgeLabel}
          onDeleteSelected={handleDeleteSelected}
          diagramMetadata={diagramMetadata}
          validationReport={validationReport}
          explanationData={explanationData}
          activeTab={activeRightTab}
          setActiveTab={setActiveRightTab}
        />
      </main>
    </div>
  );
}
