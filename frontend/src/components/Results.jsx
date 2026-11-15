import { useEffect, useState } from "react";
import { ENGINE, Icon, SEVERITY, label, rank } from "../lib/ui";

const BOX_COLOUR = {
  text: "border-indigo-500",
  visual: "border-sky-500",
  deterministic: "border-amber-500",
};

const isHandled = (f) => f.status === "accepted" || f.status === "fixed";

export function TextHighlighter({ text, findings, active, onSelect }) {
  // Dismissed findings are no longer highlighted
  const located = findings.filter(
    (f) =>
      f.status !== "dismissed" &&
      Number.isInteger(f.location?.start) &&
      f.location.start >= 0 &&
      f.location.end > f.location.start
  );
  const cuts = new Set([0, text.length]);
  located.forEach((f) => {
    cuts.add(Math.min(f.location.start, text.length));
    cuts.add(Math.min(f.location.end, text.length));
  });
  const points = [...cuts].sort((a, b) => a - b);

  return (
    <div className="whitespace-pre-wrap p-5 text-[15px] leading-8 text-slate-900">
      {points.slice(0, -1).map((start, i) => {
        const end = points[i + 1];
        const piece = text.slice(start, end);
        const covering = located.filter((f) => f.location.start <= start && f.location.end >= end);
        if (!covering.length) return <span key={start}>{piece}</span>;

        const open = covering.filter((f) => !isHandled(f));
        const lead = (open.length ? open : covering).reduce((a, b) => (rank[a.severity] <= rank[b.severity] ? a : b));
        const colour = open.length ? ENGINE[lead.source]?.mark ?? "bg-slate-200" : "bg-emerald-100";
        const isActive = covering.some((f) => f.location.group === active);
        return (
          <mark
            key={start}
            onClick={() => onSelect(lead.location.group)}
            title={covering.map((f) => f.rule?.title || f.segment_text).join(" • ")}
            className={`cursor-pointer rounded px-0.5 ${colour} ${isActive ? "ring-2 ring-blue-500" : ""}`}
          >
            {piece}
          </mark>
        );
      })}
    </div>
  );
}

export function ImageOverlay({ url, findings, active, onSelect }) {
  // Boxes are stored as fractions of the image, so they fit at any display size
  return (
    <div className="p-5">
      <div className="relative inline-block max-w-full">
        <img src={url} alt="Submitted content" className="block max-w-full rounded-lg border border-slate-200" />
        {findings.map((f, i) => {
          const box = f.location?.box;
          if (!box || f.status === "dismissed") return null;
          const [x1, y1, x2, y2] = box;
          const isActive = f.location.group === active;
          return (
            <button
              key={f.id}
              onClick={() => onSelect(f.location.group)}
              title={f.segment_text}
              style={{ left: `${x1 * 100}%`, top: `${y1 * 100}%`, width: `${(x2 - x1) * 100}%`, height: `${(y2 - y1) * 100}%` }}
              className={`absolute border-2 ${isHandled(f) ? "border-emerald-500" : BOX_COLOUR[f.source] ?? "border-slate-500"} ${isActive ? "bg-blue-400/20" : ""}`}
            >
              <span className="absolute -top-5 left-0 rounded bg-slate-900 px-1 text-xs text-white">{i + 1}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Finding({ f, n, onStatus }) {
  const engine = ENGINE[f.source] ?? ENGINE.text;
  const handled = f.status !== "open";
  const struck = f.suggested_correction && f.source !== "visual";
  const act = (e, status) => {
    e.stopPropagation();
    onStatus(f.id, status);
  };

  return (
    <div className={`py-4 first:pt-0 last:pb-0 ${f.status === "dismissed" ? "opacity-50" : ""}`}>
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide ${engine.chip}`}>{engine.full}</span>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${SEVERITY[f.severity]}`}>{f.severity}</span>
        {f.location?.page && (
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">PDF PAGE {f.location.page}</span>
        )}
        {handled && (
          <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold uppercase text-emerald-700 ring-1 ring-emerald-200">{f.status}</span>
        )}
        <span className="ml-auto text-xs text-slate-400">#{n}</span>
      </div>

      <h4 className="text-sm font-semibold text-slate-900">{f.rule?.title || label(f.finding_type)}</h4>
      <p className="mt-1 text-sm leading-6 text-slate-600">{f.explanation}</p>

      {f.rule && (
        <div className="mt-2 inline-flex max-w-full items-center gap-1.5 rounded-md bg-slate-50 px-2 py-1 text-xs text-slate-600 ring-1 ring-slate-200">
          <Icon name="book" className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">
            Source: {f.rule.brand_documents?.filename ?? "Brand guidelines"}
            {f.rule.source_page && ` · page ${f.rule.source_page}`}
          </span>
        </div>
      )}
      {f.rule?.source_excerpt && (
        <p className="mt-2 border-l-2 border-slate-300 pl-2 text-xs italic text-slate-500">“{f.rule.source_excerpt}”</p>
      )}

      {f.segment_text && (
        <div className={`mt-3 rounded-md px-3 py-2 font-mono text-xs ${struck ? "bg-red-50 text-red-700 line-through decoration-red-300" : "bg-slate-50 text-slate-700"}`}>
          {f.segment_text}
        </div>
      )}
      {f.suggested_correction && (
        <div className="mt-1.5 rounded-md bg-emerald-50 px-3 py-2 font-mono text-xs text-emerald-800">+ {f.suggested_correction}</div>
      )}

      <div className="mt-3 flex items-center gap-2">
        {handled ? (
          <button onClick={(e) => act(e, "open")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
            Reopen
          </button>
        ) : (
          <>
            <button onClick={(e) => act(e, "accepted")} className="flex-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700">
              Accept
            </button>
            <button onClick={(e) => act(e, "dismissed")} className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100">
              Dismiss
            </button>
          </>
        )}
      </div>
    </div>
  );
}

const TABS = [
  ["all", "All"],
  ["deterministic", "Deterministic"],
  ["text", "Wording AI"],
  ["visual", "Visual AI"],
];

export function FindingsList({ findings, active, onSelect, onStatus }) {
  const [tab, setTab] = useState("all");

  useEffect(() => {
    if (active) {
      document.getElementById(`group-${active}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [active]);

  if (!findings.length) {
    return (
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
        No brand issues found.
      </div>
    );
  }

  const numbered = findings.map((f, i) => ({ f, n: i + 1 }));
  const count = (key) => (key === "all" ? numbered.length : numbered.filter(({ f }) => f.source === key).length);
  const shown = tab === "all" ? numbered : numbered.filter(({ f }) => f.source === tab);

  const groups = [];
  shown.forEach(({ f, n }) => {
    const key = f.location?.group ?? f.id;
    let group = groups.find((g) => g.key === key);
    if (!group) {
      group = { key, items: [] };
      groups.push(group);
    }
    group.items.push({ f, n });
  });

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-1 border-b border-slate-200 pb-2">
        {TABS.filter(([key]) => key === "all" || count(key) > 0).map(([key, name]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`rounded-md px-2.5 py-1 text-xs font-semibold ${tab === key ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
          >
            {name} ({count(key)})
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {groups.map((g) => (
          <div
            key={g.key}
            id={`group-${g.key}`}
            onClick={() => onSelect(g.key)}
            className={`cursor-pointer rounded-lg border bg-white p-3 ${active === g.key ? "border-blue-500 ring-1 ring-blue-500" : "border-slate-200"}`}
          >
            {g.items.length > 1 && (
              <p className="mb-2 text-xs font-semibold text-purple-700">This part of the content breaks {g.items.length} rules</p>
            )}
            <div className="divide-y divide-slate-100">
              {g.items.map(({ f, n }) => (
                <Finding key={f.id} f={f} n={n} onStatus={onStatus} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}