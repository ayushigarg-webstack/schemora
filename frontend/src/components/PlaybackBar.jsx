import React from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  Sliders,
  Layers,
  Activity,
  X,
  FastForward,
} from 'lucide-react';

export default function PlaybackBar({
  traceEvents = [],
  currentStep = 0,
  isPlaying = false,
  playbackSpeed = 1,
  onPlay,
  onPause,
  onStepBack,
  onStepForward,
  onReset,
  onSeek,
  onSpeedChange,
  onClose,
}) {
  if (!traceEvents || traceEvents.length === 0) {
    return null;
  }

  const activeEvent = traceEvents[currentStep] || {};
  const variables = activeEvent.variables || {};
  const callStack = activeEvent.call_stack || ['<module>'];
  const totalSteps = traceEvents.length;

  return (
    <section className="playback-bar" aria-label="Execution Trace Stepper">
      {/* Top row: Stepper Controls & Status */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        {/* Playback Button Group */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={onReset}
            className="playback-btn"
            title="Reset to Step 0"
            aria-label="Reset trace"
          >
            <RotateCcw size={14} />
          </button>
          <button
            onClick={onStepBack}
            disabled={currentStep <= 0}
            className="playback-btn"
            title="Step Backward"
            aria-label="Step back"
          >
            <SkipBack size={14} />
          </button>
          <button
            onClick={isPlaying ? onPause : onPlay}
            className="playback-btn-primary"
            title={isPlaying ? 'Pause Execution' : 'Play Execution'}
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause size={15} /> : <Play size={15} fill="currentColor" />}
          </button>
          <button
            onClick={onStepForward}
            disabled={currentStep >= totalSteps - 1}
            className="playback-btn"
            title="Step Forward"
            aria-label="Step forward"
          >
            <SkipForward size={14} />
          </button>

          {/* Speed Selector */}
          <div className="flex items-center bg-slate-100 rounded border border-slate-200 ml-1.5 px-1 py-0.5 text-[11px] font-mono">
            {[0.5, 1, 2].map((sp) => (
              <button
                key={sp}
                onClick={() => onSpeedChange(sp)}
                className={`px-1.5 py-0.5 rounded ${playbackSpeed === sp ? 'bg-white font-bold text-blue-600 shadow-xs' : 'text-slate-600'}`}
              >
                {sp}x
              </button>
            ))}
          </div>
        </div>

        {/* Step Scrubber & Counter */}
        <div className="flex items-center gap-2.5 flex-1 min-w-[160px] max-w-sm">
          <span className="text-[11px] font-mono text-slate-500 whitespace-nowrap shrink-0">
            Step {currentStep + 1} / {totalSteps}
          </span>
          <input
            type="range"
            min="0"
            max={Math.max(0, totalSteps - 1)}
            value={currentStep}
            onChange={(e) => onSeek(parseInt(e.target.value, 10))}
            className="lucid-slider flex-1"
          />
        </div>

        {/* Call Stack Breadcrumbs */}
        <div className="flex items-center gap-1 text-[11px] text-slate-600 shrink-0">
          <Layers size={13} className="text-slate-400 shrink-0" />
          <span className="font-semibold text-slate-500 mr-1 shrink-0">Stack:</span>
          <div className="flex items-center gap-1 overflow-x-auto max-w-[200px]">
            {callStack.map((frame, i) => (
              <React.Fragment key={i}>
                {i > 0 && <span className="text-slate-300">/</span>}
                <span className="bg-slate-100 px-1.5 py-0.5 rounded font-mono text-[10px] text-slate-700 whitespace-nowrap">
                  {frame}
                </span>
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Close Button */}
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 p-1 shrink-0 ml-auto"
          title="Close Stepper"
          aria-label="Close Playback Bar"
        >
          <X size={14} />
        </button>
      </div>

      {/* Bottom row: Active Step Explanation & Variable State Watch Table */}
      <div className="playback-details-row">
        {/* Step explanation card */}
        <div className="flex items-center gap-2 flex-1 min-w-[220px]">
          <span className="badge-pill bg-blue-100 text-blue-800 font-mono text-[10px] shrink-0">
            Line {activeEvent.line_number || '?'}
          </span>
          <span className="badge-pill bg-slate-100 text-slate-700 text-[10px] uppercase font-mono shrink-0">
            {activeEvent.event_type || 'line'}
          </span>
          <p className="text-xs text-slate-800 font-medium truncate">
            {activeEvent.explanation || `Executing line ${activeEvent.line_number}`}
          </p>
        </div>

        {/* Variable Watch Inspector */}
        <div className="flex items-center gap-1.5 overflow-x-auto max-w-md shrink-0 py-0.5">
          <span className="text-[11px] font-semibold text-slate-500 whitespace-nowrap shrink-0">
            Variables:
          </span>
          {Object.keys(variables).length === 0 ? (
            <span className="text-[11px] text-slate-400 italic">none in scope</span>
          ) : (
            Object.entries(variables).map(([k, v]) => (
              <div
                key={k}
                className="bg-white border border-slate-200 rounded px-1.5 py-0.5 font-mono text-[11px] shadow-2xs whitespace-nowrap"
              >
                <span className="text-indigo-600 font-semibold">{k}</span>
                <span className="text-slate-400 mx-1">=</span>
                <span className="text-emerald-700">
                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
