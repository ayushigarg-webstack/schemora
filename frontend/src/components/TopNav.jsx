import React, { useState, useEffect, useRef } from 'react';
import {
  Share2,
  Download,
  Upload,
  Undo2,
  Redo2,
  Maximize2,
  FileCode,
  FileText,
  CheckCircle2,
  AlertCircle,
  FileJson,
  Image as ImageIcon,
} from 'lucide-react';

export default function TopNav({
  mode,
  setMode,
  title,
  setTitle,
  isDirty,
  onExport,
  onImport,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  onFitView,
  backendOnline,
}) {
  const [showExportMenu, setShowExportMenu] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowExportMenu(false);
      }
    }
    if (showExportMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showExportMenu]);

  return (
    <header className="top-nav">
      {/* Brand & Document Identity */}
      <div className="flex items-center gap-3">
        <div className="brand-logo" title="Diagram Studio">
          <Share2 size={16} className="text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="doc-title-input"
              placeholder="Untitled Diagram"
              title="Click to rename document"
            />
            <span
              className={`status-pill ${isDirty ? 'status-modified' : 'status-clean'}`}
              title={isDirty ? 'Unsaved local modifications' : 'All changes saved locally'}
            >
              {isDirty ? 'Modified' : 'Clean'}
            </span>
            <span
              className={`status-pill ${backendOnline ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'}`}
              title={backendOnline ? 'FastAPI Backend Online (Port 8000)' : 'FastAPI Backend Offline'}
            >
              {backendOnline ? 'API Online' : 'API Offline'}
            </span>
          </div>
        </div>
      </div>

      {/* Central Mode Switcher (Lucidchart-inspired dual workspace) */}
      <div className="mode-segmented-control" role="tablist">
        <button
          onClick={() => setMode('text')}
          className={`mode-btn ${mode === 'text' ? 'active' : ''}`}
          role="tab"
          aria-selected={mode === 'text'}
        >
          <FileText size={14} />
          <span>Text to Diagram</span>
        </button>
        <button
          onClick={() => setMode('code')}
          className={`mode-btn ${mode === 'code' ? 'active' : ''}`}
          role="tab"
          aria-selected={mode === 'code'}
        >
          <FileCode size={14} />
          <span>Explain Code</span>
        </button>
      </div>

      {/* Action Controls & Export */}
      <div className="flex items-center gap-2">
        <div className="flex items-center bg-slate-100 rounded-md p-0.5 border border-slate-200">
          <button
            onClick={onUndo}
            disabled={!canUndo}
            className="icon-action-btn"
            title="Undo (Ctrl+Z)"
            aria-label="Undo"
          >
            <Undo2 size={14} />
          </button>
          <button
            onClick={onRedo}
            disabled={!canRedo}
            className="icon-action-btn"
            title="Redo (Ctrl+Y)"
            aria-label="Redo"
          >
            <Redo2 size={14} />
          </button>
        </div>

        <button
          onClick={onFitView}
          className="icon-action-btn border border-slate-200"
          title="Fit to View (F)"
          aria-label="Fit to View"
        >
          <Maximize2 size={14} />
        </button>

        <label className="import-action-btn" title="Import Diagram JSON">
          <Upload size={14} />
          <span>Import</span>
          <input
            type="file"
            accept=".json"
            onChange={onImport}
            className="hidden"
          />
        </label>

        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            className="export-primary-btn"
            aria-expanded={showExportMenu}
            aria-haspopup="true"
          >
            <Download size={14} />
            <span>Export</span>
          </button>

          {showExportMenu && (
            <div className="export-dropdown-menu" role="menu">
              <button
                onClick={() => {
                  onExport('png');
                  setShowExportMenu(false);
                }}
                className="dropdown-item flex items-center gap-2"
                role="menuitem"
              >
                <ImageIcon size={14} className="text-slate-500" />
                <span>PNG Image (.png)</span>
              </button>
              <button
                onClick={() => {
                  onExport('svg');
                  setShowExportMenu(false);
                }}
                className="dropdown-item flex items-center gap-2"
                role="menuitem"
              >
                <ImageIcon size={14} className="text-slate-500" />
                <span>SVG Vector (.svg)</span>
              </button>
              <div className="dropdown-divider" />
              <button
                onClick={() => {
                  onExport('json');
                  setShowExportMenu(false);
                }}
                className="dropdown-item flex items-center gap-2 font-medium text-blue-600"
                role="menuitem"
              >
                <FileJson size={14} className="text-blue-600" />
                <span>Diagram IR JSON (.json)</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
