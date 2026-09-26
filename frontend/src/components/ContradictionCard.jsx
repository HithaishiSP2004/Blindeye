import React from 'react';

export default function ContradictionCard({ finding, onSelectSource, selectedSource }) {
  if (!finding) return null;

  const isConflict = finding.status === 'CONFIRMED_CONFLICT';
  const isInsufficient = finding.status === 'INSUFFICIENT_CONTEXT';
  const isNoConflict = finding.status === 'NO_CONFLICT';

  const badgeStyle = isConflict
    ? 'bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-950/40 dark:text-amber-200 dark:border-amber-800'
    : isInsufficient
    ? 'bg-stone-100 text-stone-800 border-stone-300 dark:bg-stone-800 dark:text-stone-300 dark:border-stone-700'
    : 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800';

  const badgeText = isConflict
    ? 'Review Required'
    : isInsufficient
    ? 'Context Incomplete'
    : 'Harmonious Terms';

  const subjectLabel = (finding.subject || 'OTHER')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const isSourceASelected = selectedSource && selectedSource.clause_id === finding.source_a.clause_id;
  const isSourceBSelected = selectedSource && selectedSource.clause_id === finding.source_b.clause_id;

  return (
    <div
      className={`p-4 rounded-xl border transition-all duration-200 ${
        isConflict
          ? 'bg-amber-50/40 border-amber-200/80 dark:bg-stone-900/80 dark:border-amber-900/40 shadow-sm'
          : 'bg-white/80 border-stone-200/80 dark:bg-stone-900/40 dark:border-stone-800'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="font-serif font-semibold text-stone-900 dark:text-stone-100 text-sm">
            {subjectLabel}
          </span>
          {finding.actor && finding.actor !== 'UNKNOWN' && (
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 font-mono">
              Actor: {finding.actor.toLowerCase()}
            </span>
          )}
        </div>
        <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${badgeStyle}`}>
          {badgeText}
        </span>
      </div>

      {/* Visual Evidence Relationship Diagram */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 rounded-lg bg-stone-50/70 dark:bg-stone-950/40 border border-stone-200/60 dark:border-stone-800/80 my-2">
        {/* Source Statement A */}
        <div
          className={`flex flex-col justify-between p-3 rounded-lg border transition-all ${
            isSourceASelected
              ? 'bg-amber-100/60 border-amber-400 dark:bg-amber-950/40 dark:border-amber-700 ring-2 ring-amber-400/30'
              : 'bg-white dark:bg-stone-900 border-stone-200 dark:border-stone-800'
          }`}
        >
          <div>
            <div className="flex items-center justify-between text-[11px] text-stone-500 dark:text-stone-400 mb-1">
              <span className="font-mono font-medium">
                {finding.source_a.clause_number ? `Clause ${finding.source_a.clause_number}` : 'Passage A'}
              </span>
              <span>Page {finding.source_a.page_number}</span>
            </div>
            <div className="text-sm font-semibold text-stone-800 dark:text-stone-200 mb-1.5">
              {finding.value_a}
            </div>
            <p className="text-xs text-stone-600 dark:text-stone-400 italic line-clamp-3 font-serif">
              "{finding.source_a.exact_quote}"
            </p>
          </div>
          <button
            type="button"
            onClick={() => onSelectSource(finding.source_a)}
            className="mt-3 text-[11px] font-medium text-amber-800 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-200 flex items-center gap-1 self-start"
          >
            <span>View source A</span>
            <span>&rarr;</span>
          </button>
        </div>

        {/* Source Statement B */}
        <div
          className={`flex flex-col justify-between p-3 rounded-lg border transition-all ${
            isSourceBSelected
              ? 'bg-amber-100/60 border-amber-400 dark:bg-amber-950/40 dark:border-amber-700 ring-2 ring-amber-400/30'
              : 'bg-white dark:bg-stone-900 border-stone-200 dark:border-stone-800'
          }`}
        >
          <div>
            <div className="flex items-center justify-between text-[11px] text-stone-500 dark:text-stone-400 mb-1">
              <span className="font-mono font-medium">
                {finding.source_b.clause_number ? `Clause ${finding.source_b.clause_number}` : 'Passage B'}
              </span>
              <span>Page {finding.source_b.page_number}</span>
            </div>
            <div className="text-sm font-semibold text-stone-800 dark:text-stone-200 mb-1.5">
              {finding.value_b}
            </div>
            <p className="text-xs text-stone-600 dark:text-stone-400 italic line-clamp-3 font-serif">
              "{finding.source_b.exact_quote}"
            </p>
          </div>
          <button
            type="button"
            onClick={() => onSelectSource(finding.source_b)}
            className="mt-3 text-[11px] font-medium text-amber-800 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-200 flex items-center gap-1 self-start"
          >
            <span>View source B</span>
            <span>&rarr;</span>
          </button>
        </div>
      </div>

      {/* Factual Non-Adjudicating Explanation */}
      <p className="text-xs text-stone-700 dark:text-stone-300 mt-2.5 leading-relaxed">
        {finding.explanation}
      </p>
    </div>
  );
}
