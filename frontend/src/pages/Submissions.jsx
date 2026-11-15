import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { FindingChips, STATUS_LABEL, StatusBadge, VisibilityBadge, timeAgo } from "../lib/ui";

const FILTERS = ["all", "in_review", "needs_revision", "approved", "rejected", "draft"];

export default function Submissions({ mode = "all" }) {
  const queue = mode === "queue";
  const [filter, setFilter] = useState("all");
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");

  const status = queue ? "in_review" : filter;

  useEffect(() => {
    setItems(null);
    setError("");
    api(`/dashboard/queue?status=${status}`).then(setItems).catch((e) => setError(e.message));
  }, [status]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">{queue ? "Review Queue" : "All Submissions"}</h2>
          <p className="mt-1 text-sm text-slate-600">
            {queue ? "Content that has been checked and is waiting for human sign-off." : "Every submission in this workspace."}
          </p>
        </div>
        {!queue && (
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-full px-3 py-1.5 text-xs font-medium ${filter === f ? "bg-slate-900 text-white" : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"}`}
              >
                {f === "all" ? "All" : STATUS_LABEL[f]}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!items && !error && <div className="h-48 animate-pulse rounded-xl bg-slate-100" />}

      {items && items.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center text-sm text-slate-500">
          {queue ? "The queue is empty. Nothing is waiting for sign-off." : "No submissions match this filter."}
        </div>
      )}

      {items && items.length > 0 && queue && (
        <div className="grid gap-5 md:grid-cols-2">
          {items.map((s) => (
            <Link
              key={s.id}
              to={`/submissions/${s.id}`}
              className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <StatusBadge value={s.status} />
                <span className="text-xs text-slate-400">{timeAgo(s.updated_at)}</span>
              </div>
              <h3 className="mt-3 font-semibold text-slate-900">{s.title || "Untitled"}</h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Submitted by {s.created_by_name || "unknown"} • {s.content_type} • v{s.current_version}
              </p>
              {s.excerpt && (
                <p className="mt-3 line-clamp-3 rounded-lg bg-slate-50 p-3 font-mono text-xs leading-5 text-slate-600">{s.excerpt}</p>
              )}
              <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-4 mt-4">
                <div className="flex items-center gap-2 text-sm">
                  {s.findings.analyzed ? (
                    <>
                      <span className="font-medium text-slate-900">{s.findings.open} Open Findings</span>
                      {s.findings.open_high > 0 && (
                        <span className="rounded bg-red-50 px-1.5 py-0.5 text-[11px] font-semibold text-red-700">{s.findings.open_high} HIGH</span>
                      )}
                    </>
                  ) : (
                    <span className="text-slate-400">Not analysed yet</span>
                  )}
                </div>
                <span className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">
                  Inspect & Sign Off →
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {items && items.length > 0 && !queue && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3 font-semibold">Content title</th>
                <th className="px-3 py-3 font-semibold">Author</th>
                <th className="px-3 py-3 font-semibold">Engine findings</th>
                <th className="px-3 py-3 font-semibold">Status</th>
                <th className="px-5 py-3 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50">
                  <td className="px-5 py-4">
                    <div className="font-semibold text-slate-900">{s.title || "Untitled"}</div>
                    <div className="text-xs text-slate-500">{s.content_type} • v{s.current_version} • Updated {timeAgo(s.updated_at)}</div>
                  </td>
                  <td className="px-3 py-4 font-medium text-slate-800">{s.created_by_name || "—"}</td>
                  <td className="px-3 py-4"><FindingChips stats={s.findings} /></td>
                  <td className="px-3 py-4">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <StatusBadge value={s.status} />
                      <VisibilityBadge value={s.visibility} />
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <Link to={`/submissions/${s.id}`} className="text-sm font-semibold text-blue-700 hover:underline">Inspect →</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}