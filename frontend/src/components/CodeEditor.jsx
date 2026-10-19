import React from 'react';
import { Play, Sparkles } from 'lucide-react';

export default function CodeEditor({
  code,
  onChange,
  activeLineNumber,
  selectedLineRange,
  onLineClick,
  disabled = false,
}) {
  const lines = code.split('\n');

  return (
    <div className="code-editor-wrapper">
      <div className="code-editor-gutter">
        {lines.map((_, idx) => {
          const lineNum = idx + 1;
          const isActive = activeLineNumber === lineNum;
          const isSelected =
            selectedLineRange &&
            lineNum >= selectedLineRange.start &&
            lineNum <= selectedLineRange.end;

          return (
            <div
              key={lineNum}
              onClick={() => onLineClick && onLineClick(lineNum)}
              className={`gutter-line ${isActive ? 'active' : ''} ${isSelected ? 'selected' : ''}`}
            >
              <span className="line-num">{lineNum}</span>
              {isActive && <span className="active-arrow">▶</span>}
            </div>
          );
        })}
      </div>

      <div className="code-editor-text-area relative flex-1">
        <textarea
          value={code}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          spellCheck={false}
          className="code-textarea font-mono text-xs leading-5"
          rows={Math.max(12, lines.length + 2)}
        />
      </div>
    </div>
  );
}
