export const SEVERITY = {
  high: "bg-red-50 text-red-700 ring-1 ring-red-200",
  medium: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
  low: "bg-sky-50 text-sky-700 ring-1 ring-sky-200",
};
export const HIGHLIGHT = { high: "bg-red-200", medium: "bg-amber-200", low: "bg-sky-200" };

export const STATUS = {
  draft: "bg-slate-100 text-slate-700 ring-1 ring-slate-200",
  analyzing: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
  in_review: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
  approved: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  needs_revision: "bg-rose-50 text-rose-700 ring-1 ring-rose-200",
  rejected: "bg-red-50 text-red-700 ring-1 ring-red-200",
};
export const STATUS_LABEL = {
  draft: "Draft",
  analyzing: "Analysing",
  in_review: "In Review",
  approved: "Approved",
  needs_revision: "Changes Requested",
  rejected: "Rejected",
};

export const rank = { high: 0, medium: 1, low: 2 };

export const label = (s) => String(s).replace(/_/g, " ");
export const fmt = (d) => new Date(d).toLocaleString();
export const fmtDate = (d) =>
  new Date(d).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });

export function timeAgo(d) {
  const s = Math.max(1, Math.floor((Date.now() - new Date(d).getTime()) / 1000));
  for (const [name, size] of [["day", 86400], ["hour", 3600], ["min", 60]]) {
    if (s >= size) {
      const n = Math.floor(s / size);
      return `${n} ${name}${n > 1 ? "s" : ""} ago`;
    }
  }
  return "just now";
}

export function Badge({ className = "", children }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs ${className}`}>{children}</span>;
}

export function StatusBadge({ value }) {
  return <Badge className={`font-medium ${STATUS[value] ?? STATUS.draft}`}>{STATUS_LABEL[value] ?? label(value)}</Badge>;
}

// The three engines that produce findings, named for what they really are
export const ENGINE = {
  deterministic: {
    name: "Deterministic",
    full: "DETERMINISTIC CHECK",
    chip: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
    mark: "bg-amber-200",
  },
  text: {
    name: "Wording AI",
    full: "GEMINI · RAG CITED",
    chip: "bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200",
    mark: "bg-indigo-100 underline decoration-indigo-500 decoration-2 underline-offset-2",
  },
  visual: {
    name: "Visual AI",
    full: "GEMINI VISION",
    chip: "bg-sky-50 text-sky-700 ring-1 ring-sky-200",
    mark: "bg-sky-200",
  },
};

const ICONS = {
  lock: (<><rect x="4" y="9" width="12" height="8" rx="2" /><path d="M7 9V6a3 3 0 016 0v3" /></>),
  link: (<><path d="M8.5 11.5a3 3 0 004.2 0l3-3a3 3 0 00-4.2-4.2l-1 1" /><path d="M11.5 8.5a3 3 0 00-4.2 0l-3 3a3 3 0 004.2 4.2l1-1" /></>),
  globe: (<><circle cx="10" cy="10" r="8" /><path d="M2 10h16M10 2c2.5 2.2 2.5 13.8 0 16M10 2c-2.5 2.2-2.5 13.8 0 16" /></>),
  doc: (<><path d="M5 2h7l4 4v12H5z" /><path d="M12 2v4h4M8 10h5M8 13h5" /></>),
  search: (<><circle cx="9" cy="9" r="6" /><path d="M14 14l4 4" /></>),
  check: <path d="M4 10.5l4 4 8-9" />,
  copy: (<><rect x="7" y="7" width="10" height="10" rx="2" /><path d="M13 7V5a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2" /></>),
  dashboard: (<><rect x="3" y="3" width="6" height="6" rx="1.5" /><rect x="11" y="3" width="6" height="6" rx="1.5" /><rect x="3" y="11" width="6" height="6" rx="1.5" /><rect x="11" y="11" width="6" height="6" rx="1.5" /></>),
  plus: <path d="M10 4v12M4 10h12" />,
  queue: (<><rect x="4" y="3" width="12" height="14" rx="2" /><path d="M7 8h6M7 11h6M7 14h3" /></>),
  book: (<><path d="M3 4h5a2 2 0 012 2v11a2 2 0 00-2-2H3z" /><path d="M17 4h-5a2 2 0 00-2 2v11a2 2 0 012-2h5z" /></>),
  shield: (<><path d="M10 2l6 2.5v5c0 4-2.6 6.8-6 8-3.4-1.2-6-4-6-8v-5z" /><path d="M7.5 10l1.8 1.8L13 8.2" /></>),
  clock: (<><circle cx="10" cy="10" r="8" /><path d="M10 5.5V10l3 2" /></>),
  alert: (<><path d="M10 3l8 14H2z" /><path d="M10 8v4M10 14.5v.01" /></>),
  info: (<><circle cx="10" cy="10" r="8" /><path d="M10 9v5M10 6v.01" /></>),
  arrow: <path d="M4 10h12M11 5l5 5-5 5" />,
};

export function Icon({ name, className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

export const VISIBILITY = {
  private: { label: "Private", icon: "lock", className: "bg-slate-100 text-slate-700" },
  unlisted: { label: "Unlisted", icon: "link", className: "bg-amber-100 text-amber-800" },
  public: { label: "Public", icon: "globe", className: "bg-green-100 text-green-800" },
};

export function VisibilityBadge({ value }) {
  const v = VISIBILITY[value] ?? VISIBILITY.private;
  return (
    <Badge className={`inline-flex items-center gap-1 ${v.className}`}>
      <Icon name={v.icon} className="h-3 w-3" /> {v.label}
    </Badge>
  );
}

// Compact "what did the engines find" chips for tables and cards
export function FindingChips({ stats }) {
  if (!stats?.analyzed) return <span className="text-xs text-slate-400">Not analysed</span>;
  if (stats.total === 0) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
        <Icon name="check" className="h-3.5 w-3.5" /> 0 issues
      </span>
    );
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {Object.entries(ENGINE).map(
        ([key, e]) =>
          stats.by_source?.[key] > 0 && (
            <span key={key} className={`rounded-md px-2 py-0.5 text-xs font-medium ${e.chip}`}>
              {stats.by_source[key]} {e.name}
            </span>
          )
      )}
    </div>
  );
}