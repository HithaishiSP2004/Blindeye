import React, { useState } from 'react';
import ContradictionCard from './ContradictionCard';

export default function ContradictionPanel({ contradictionData, onSelectSource, selectedSource }) {
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'CONFLICTS' | 'HARMONIOUS'

  if (!contradictionData) {
    return (
      <div className="p-8 text-center text-stone-500 dark:text-stone-400">
        <p className="font-serif text-sm">Upload or analyze a document to view contradiction intelligence.</p>
      </div>
    );
  }

  const { findings = [], total_conflicts = 0, evaluation_summary = '' } = contradictionData;

  const conflictsOnly = findings.filter((f) => f.status === 'CONFIRMED_CONFLICT');
  const harmoniousOnly = findings.filter((f) => f.status === 'NO_CONFLICT');

  const displayedFindings =
    filter === 'CONFLICTS'
      ? conflictsOnly
      : filter === 'HARMONIOUS'
      ? harmoniousOnly
      : findings;

  return (
    <div className="flex flex-col h-full overflow-y-auto pr-1">
      {/* Editorial Overview Header */}
      <div className="p-4 mb-3 rounded-xl bg-stone-100/60 dark:bg-stone-900/40 border border-stone-200/80 dark:border-stone-800">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="font-serif font-semibold text-stone-900 dark:text-stone-100 text-sm">
            Evidence Relationships & Conflicts
          </span>
          <span
            className={`text-xs font-mono font-medium px-2 py-0.5 rounded-full ${
              total_conflicts > 0
                ? 'bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-200'
                : 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-200'
            }`}
          >
            {total_conflicts === 1 ? '1 Conflict' : `${total_conflicts} Conflicts`}
          </span>
        </div>
        <p className="text-xs text-stone-600 dark:text-stone-400 leading-relaxed font-sans">
          {evaluation_summary || 'Comparing paired contractual provisions across actors, subjects, and scopes.'}
        </p>
      </div>

      {/* Filter Tabs */}
      {findings.length > 0 && (
        <div className="flex items-center gap-1.5 mb-3 text-xs">
          <button
            type="button"
            onClick={() => setFilter('ALL')}
            className={`px-3 py-1 rounded-md transition-colors ${
              filter === 'ALL'
                ? 'bg-stone-800 text-white dark:bg-stone-200 dark:text-stone-900 font-medium'
                : 'bg-stone-100 dark:bg-stone-900 text-stone-600 dark:text-stone-400 hover:bg-stone-200'
            }`}
          >
            All Findings ({findings.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('CONFLICTS')}
            className={`px-3 py-1 rounded-md transition-colors ${
              filter === 'CONFLICTS'
                ? 'bg-amber-800 text-white dark:bg-amber-200 dark:text-amber-950 font-medium'
                : 'bg-stone-100 dark:bg-stone-900 text-stone-600 dark:text-stone-400 hover:bg-stone-200'
            }`}
          >
            Conflicts ({conflictsOnly.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('HARMONIOUS')}
            className={`px-3 py-1 rounded-md transition-colors ${
              filter === 'HARMONIOUS'
                ? 'bg-emerald-800 text-white dark:bg-emerald-200 dark:text-emerald-950 font-medium'
                : 'bg-stone-100 dark:bg-stone-900 text-stone-600 dark:text-stone-400 hover:bg-stone-200'
            }`}
          >
            Harmonious ({harmoniousOnly.length})
          </button>
        </div>
      )}

      {/* Findings List */}
      {displayedFindings.length === 0 ? (
        <div className="p-8 text-center border rounded-xl border-dashed border-stone-200 dark:border-stone-800 my-4">
          <p className="text-sm font-serif text-stone-600 dark:text-stone-300 mb-1">
            No conflicting statements detected.
          </p>
          <p className="text-xs text-stone-500 dark:text-stone-400">
            All extracted contractual provisions maintain consistent values and actor attributions.
          </p>
        </div>
      ) : (
        <div className="space-y-3 pb-6">
          {displayedFindings.map((finding) => (
            <ContradictionCard
              key={finding.finding_id}
              finding={finding}
              onSelectSource={onSelectSource}
              selectedSource={selectedSource}
            />
          ))}
        </div>
      )}
    </div>
  );
}
