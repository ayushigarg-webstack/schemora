import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import {
  Server,
  Database,
  Globe,
  HardDrive,
  Cpu,
  Layers,
  ArrowRightCircle,
  HelpCircle,
  Activity,
  Code2,
  Share2,
  Table,
  Key,
  Network,
  ShieldCheck,
  Wifi,
  Box,
  GitFork,
  CheckCircle2,
  User,
  Monitor,
} from 'lucide-react';

/**
 * 1. Flowchart Node: Process, Decision, Terminal
 */
export const FlowchartNode = memo(({ data, selected }) => {
  const type = (data.nodeType || 'process').toLowerCase();
  const isDecision = type === 'decision' || type === 'condition';
  const isTerminal = type === 'terminal' || type === 'start' || type === 'end';
  const isActive = data.isActiveStep;

  if (isDecision) {
    return (
      <div
        className={`decision-node ${selected ? 'selected' : ''} ${isActive ? 'active-step' : ''}`}
        title={data.label}
      >
        <Handle type="target" position={Position.Top} className="flow-handle" />
        <Handle type="source" position={Position.Bottom} id="bottom" className="flow-handle" />
        <Handle type="source" position={Position.Left} id="left" className="flow-handle" />
        <Handle type="source" position={Position.Right} id="right" className="flow-handle" />
        <div className="decision-inner">
          <HelpCircle className="node-icon text-amber-600 mb-0.5" size={13} />
          <span className="node-label text-[11px] font-semibold text-slate-800 leading-tight">
            {data.label}
          </span>
        </div>
      </div>
    );
  }

  if (isTerminal) {
    const isStart = type === 'start' || data.label?.toLowerCase().includes('start');
    return (
      <div
        className={`terminal-node ${selected ? 'selected' : ''} ${isActive ? 'active-step' : ''}`}
        title={data.label}
      >
        <Handle type="target" position={Position.Top} className="flow-handle" />
        <Handle type="source" position={Position.Bottom} className="flow-handle" />
        <div className="flex items-center gap-1.5 px-1">
          {isStart ? (
            <ArrowRightCircle size={14} className="text-emerald-600 shrink-0" />
          ) : (
            <CheckCircle2 size={14} className="text-slate-600 shrink-0" />
          )}
          <span className="node-label font-bold text-xs text-slate-800 tracking-tight">
            {data.label}
          </span>
        </div>
      </div>
    );
  }

  // Standard process rectangle
  return (
    <div
      className={`process-node ${selected ? 'selected' : ''} ${isActive ? 'active-step' : ''}`}
      title={data.label}
    >
      <Handle type="target" position={Position.Top} className="flow-handle" />
      <Handle type="source" position={Position.Bottom} className="flow-handle" />
      <Handle type="target" position={Position.Left} id="left" className="flow-handle" />
      <Handle type="source" position={Position.Right} id="right" className="flow-handle" />
      <div className="node-header">
        <Activity size={11} className="text-blue-500 shrink-0" />
        <span className="node-type-tag">process</span>
      </div>
      <div className="node-label font-medium text-xs text-slate-800 mt-1 leading-snug">
        {data.label}
      </div>
    </div>
  );
});

FlowchartNode.displayName = 'FlowchartNode';

/**
 * 2. Software Architecture Node: Service, Database, Gateway, Client, Cache
 */
export const ArchitectureNode = memo(({ data, selected }) => {
  const type = (data.nodeType || 'service').toLowerCase();

  const getTheme = () => {
    if (type.includes('database') || type.includes('db') || type.includes('postgres') || type.includes('sql')) {
      return { icon: Database, color: 'text-sky-600', badgeClass: 'arch-badge-cyan' };
    }
    if (type.includes('cache') || type.includes('redis') || type.includes('memcached')) {
      return { icon: HardDrive, color: 'text-rose-600', badgeClass: 'arch-badge-rose' };
    }
    if (type.includes('gateway') || type.includes('proxy') || type.includes('balancer') || type.includes('ingress')) {
      return { icon: Globe, color: 'text-purple-600', badgeClass: 'arch-badge-purple' };
    }
    if (type.includes('client') || type.includes('frontend') || type.includes('ui') || type.includes('browser')) {
      return { icon: Layers, color: 'text-emerald-600', badgeClass: 'arch-badge-emerald' };
    }
    return { icon: Server, color: 'text-indigo-600', badgeClass: 'arch-badge-indigo' };
  };

  const { icon: Icon, color, badgeClass } = getTheme();

  return (
    <div className={`arch-node ${selected ? 'selected' : ''}`} title={data.label}>
      <Handle type="target" position={Position.Top} className="flow-handle" />
      <Handle type="source" position={Position.Bottom} className="flow-handle" />
      <Handle type="target" position={Position.Left} id="left" className="flow-handle" />
      <Handle type="source" position={Position.Right} id="right" className="flow-handle" />

      <div className="arch-node-header">
        <div className="flex items-center gap-1.5">
          <Icon size={14} className={`${color} shrink-0`} />
          <span className={`arch-badge ${badgeClass}`}>{data.nodeType || 'service'}</span>
        </div>
      </div>
      <div className="node-label font-semibold text-xs text-slate-800 mt-1.5">
        {data.label}
      </div>
      {data.attributes && Object.keys(data.attributes).length > 0 && (
        <div className="mt-1 pt-1 border-t border-slate-100 flex flex-wrap gap-1">
          {Object.entries(data.attributes).slice(0, 2).map(([k, v]) => (
            <span key={k} className="text-[10px] text-slate-500 font-mono">
              {k}: {String(v)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
});

ArchitectureNode.displayName = 'ArchitectureNode';

/**
 * 3. Concept Map Node: Semantic Ontologies & Propositions
 */
export const ConceptNode = memo(({ data, selected }) => {
  return (
    <div className={`concept-node ${selected ? 'selected' : ''}`} title={data.label}>
      <Handle type="target" position={Position.Top} className="flow-handle" />
      <Handle type="source" position={Position.Bottom} className="flow-handle" />
      <Handle type="target" position={Position.Left} id="left" className="flow-handle" />
      <Handle type="source" position={Position.Right} id="right" className="flow-handle" />
      <div className="flex items-center gap-1.5 justify-center">
        <Share2 size={12} className="text-indigo-500 shrink-0" />
        <span className="font-semibold text-xs text-slate-800">{data.label}</span>
      </div>
    </div>
  );
});

ConceptNode.displayName = 'ConceptNode';

/**
 * 4. Sequence Diagram Node: Lifeline & Participant Actor
 */
export const SequenceNode = memo(({ data, selected }) => {
  const isActor = data.nodeType === 'actor' || data.label?.toLowerCase().includes('user') || data.label?.toLowerCase().includes('client');

  return (
    <div className={`sequence-node ${selected ? 'selected' : ''}`} title={data.label}>
      <Handle type="target" position={Position.Top} className="flow-handle" />
      <Handle type="source" position={Position.Bottom} className="flow-handle" />
      <Handle type="target" position={Position.Left} id="left" className="flow-handle" />
      <Handle type="source" position={Position.Right} id="right" className="flow-handle" />

      <div className="sequence-header flex items-center justify-center gap-1.5">
        {isActor ? (
          <User size={13} className="text-blue-600 shrink-0" />
        ) : (
          <Monitor size={13} className="text-slate-600 shrink-0" />
        )}
        <span className="font-semibold text-xs text-slate-800">{data.label}</span>
      </div>
      <div className="sequence-lifeline" />
    </div>
  );
});

SequenceNode.displayName = 'SequenceNode';

/**
 * 5. ER Diagram Node: Database Entities & Schema Tables
 */
export const ERNode = memo(({ data, selected }) => {
  const attributes = data.attributes && typeof data.attributes === 'object' ? data.attributes : {};
  const fieldList = Object.keys(attributes).length > 0
    ? Object.entries(attributes)
    : [
        ['id', 'PK uuid'],
        ['name', 'varchar(255)'],
        ['created_at', 'timestamp'],
      ];

  return (
    <div className={`er-node ${selected ? 'selected' : ''}`} title={data.label}>
      <Handle type="target" position={Position.Top} className="flow-handle" />
      <Handle type="source" position={Position.Bottom} className="flow-handle" />
      <Handle type="target" position={Position.Left} id="left" className="flow-handle" />
      <Handle type="source" position={Position.Right} id="right" className="flow-handle" />

      <div className="er-header">
        <Table size={13} className="text-sky-600 shrink-0" />
        <span className="er-title font-bold text-xs text-slate-800">{data.label}</span>
      </div>
      <div className="er-fields">
        {fieldList.map(([key, val], idx) => {
          const isPk = String(val).includes('PK') || key === 'id';
          return (
            <div key={idx} className="er-row">
              <span className="flex items-center gap-1 font-mono text-[11px] text-slate-700">
                {isPk ? <Key size={10} className="text-amber-500 shrink-0" /> : <span className="w-2.5" />}
                {key}
              </span>
              <span className="font-mono text-[10px] text-slate-400">{String(val)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
});

ERNode.displayName = 'ERNode';

/**
 * 6. Network Topology Node: Routers, Switches, Firewalls, Workstations
 */
export const NetworkNode = memo(({ data, selected }) => {
  const type = (data.nodeType || 'device').toLowerCase();

  const getNetworkIcon = () => {
    if (type.includes('firewall') || type.includes('security')) {
      return { icon: ShieldCheck, color: 'text-amber-600', label: 'Firewall' };
    }
    if (type.includes('switch') || type.includes('bridge')) {
      return { icon: Network, color: 'text-indigo-600', label: 'Switch' };
    }
    if (type.includes('router') || type.includes('gateway')) {
      return { icon: Wifi, color: 'text-blue-600', label: 'Router' };
    }
    if (type.includes('workstation') || type.includes('pc') || type.includes('host')) {
      return { icon: Monitor, color: 'text-slate-600', label: 'Host' };
    }
    return { icon: Server, color: 'text-emerald-600', label: 'Server' };
  };

  const { icon: Icon, color, label } = getNetworkIcon();

  return (
    <div className={`network-node ${selected ? 'selected' : ''}`} title={data.label}>
      <Handle type="target" position={Position.Top} className="flow-handle" />
      <Handle type="source" position={Position.Bottom} className="flow-handle" />
      <Handle type="target" position={Position.Left} id="left" className="flow-handle" />
      <Handle type="source" position={Position.Right} id="right" className="flow-handle" />

      <div className="network-inner flex items-center gap-2">
        <div className="network-icon-wrap">
          <Icon size={16} className={color} />
        </div>
        <div className="network-meta">
          <div className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
            {data.nodeType || label}
          </div>
          <div className="font-bold text-xs text-slate-800">{data.label}</div>
        </div>
      </div>
    </div>
  );
});

NetworkNode.displayName = 'NetworkNode';

/**
 * 7. Dependency Graph Node: DAG Packages, Build Steps, Modules
 */
export const DependencyNode = memo(({ data, selected }) => {
  return (
    <div className={`dependency-node ${selected ? 'selected' : ''}`} title={data.label}>
      <Handle type="target" position={Position.Top} className="flow-handle" />
      <Handle type="source" position={Position.Bottom} className="flow-handle" />
      <Handle type="target" position={Position.Left} id="left" className="flow-handle" />
      <Handle type="source" position={Position.Right} id="right" className="flow-handle" />

      <div className="flex items-center gap-1.5 justify-between">
        <div className="flex items-center gap-1.5">
          <Box size={13} className="text-purple-600 shrink-0" />
          <span className="font-semibold text-xs text-slate-800">{data.label}</span>
        </div>
        <span className="dep-badge">pkg</span>
      </div>
    </div>
  );
});

DependencyNode.displayName = 'DependencyNode';

/**
 * 8. Code Block Node: Control Flow Graph (CFG) & Call Graph
 * Highlighted with ring when active during step execution.
 */
export const CodeNode = memo(({ data, selected }) => {
  const lineNo = data.sourceLocation?.line_start;
  const isActive = data.isActiveStep;
  const hasExecutionState = !!data.executionState;

  return (
    <div
      className={`code-node ${selected ? 'selected' : ''} ${isActive ? 'active-step-ring' : ''}`}
      title={data.label}
    >
      <Handle type="target" position={Position.Top} className="flow-handle" />
      <Handle type="source" position={Position.Bottom} className="flow-handle" />
      <Handle type="target" position={Position.Left} id="left" className="flow-handle" />
      <Handle type="source" position={Position.Right} id="right" className="flow-handle" />

      <div className="code-node-header">
        <div className="flex items-center gap-1">
          <Code2 size={12} className={isActive ? 'text-amber-400' : 'text-slate-400'} />
          <span className="code-type-tag">{data.nodeType || 'statement'}</span>
        </div>
        {lineNo && <span className="code-line-badge">L{lineNo}</span>}
      </div>

      <div className="code-snippet font-mono text-xs">{data.label}</div>

      {hasExecutionState && (
        <div className="code-node-state">
          <div className="text-[10px] text-emerald-400 font-mono">
            {Object.keys(data.executionState.variables || {})
              .slice(0, 2)
              .map((k) => `${k}=${JSON.stringify(data.executionState.variables[k])}`)
              .join(', ')}
          </div>
        </div>
      )}
    </div>
  );
});

CodeNode.displayName = 'CodeNode';
