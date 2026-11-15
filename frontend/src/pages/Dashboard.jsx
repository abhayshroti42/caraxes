import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { FindingChips, Icon, StatusBadge, timeAgo } from "../lib/ui";

const SUBTITLE = "Submit content, review brand checks, and manage your brand knowledge — all in one place.";

function Stat({ title, value, note, noteClass, icon, iconClass }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between text-sm text-slate-600">
        {title}
        <Icon name={icon} className={`h-5 w-5 ${iconClass}`} />
      </div>
      <div className="mt-3 text-3xl font-bold text-slate-900">{value}</div>
      <div className={`mt-1 text-xs ${noteClass}`}>{note}</div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/dashboard/stats").then(setStats).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!stats) return <div className="h-64 animate-pulse rounded-xl bg-slate-100" />;

  const total = Object.values(stats.submissions).reduce((a, b) => a + b, 0);
  const pending = stats.submissions.in_review ?? 0;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-widest text-blue-700">Brand Governance OS</div>
          <h2 className="mt-1 text-2xl font-bold text-slate-900">Welcome back</h2>
          <p className="mt-1 text-sm text-slate-600">{SUBTITLE}</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/queue" className="text-sm font-semibold text-slate-900 hover:underline">Review Queue ({pending})</Link>
          <Link to="/submit" className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800">
            <Icon name="plus" /> Submit Content
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat title="Total Submissions" value={total} note="Across text, image & PDF" noteClass="text-slate-500" icon="doc" iconClass="text-slate-700" />
        <Stat title="Pending Human Sign-Off" value={pending} note="Awaiting reviewer action" noteClass="text-amber-700" icon="clock" iconClass="text-amber-500" />
        <Stat title="Open Pre-Pub Findings" value={stats.open_findings} note="In items under review or needing changes" noteClass="text-blue-700" icon="alert" iconClass="text-blue-500" />
        <Stat title="Approved Knowledge Items" value={stats.knowledge.approved ?? 0} note={`${stats.knowledge.pending ?? 0} awaiting admin approval`} noteClass="text-emerald-700" icon="book" iconClass="text-emerald-500" />
      </div>

      <section>
        <div className="mb-3">
          <h3 className="font-semibold text-slate-900">Recent Content Submissions</h3>
          <p className="text-xs text-slate-500">Click any item to inspect findings, corrections and the audit history.</p>
        </div>
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full min-w-[720px] text-left text-sm">
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
              {stats.recent.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50">
                  <td className="px-5 py-4">
                    <div className="font-semibold text-slate-900">{s.title || "Untitled"}</div>
                    <div className="text-xs text-slate-500">{s.content_type} • v{s.current_version} • Updated {timeAgo(s.updated_at)}</div>
                  </td>
                  <td className="px-3 py-4 font-medium text-slate-800">{s.created_by_name || "—"}</td>
                  <td className="px-3 py-4"><FindingChips stats={s.findings} /></td>
                  <td className="px-3 py-4"><StatusBadge value={s.status} /></td>
                  <td className="px-5 py-4 text-right">
                    <Link to={`/submissions/${s.id}`} className="text-sm font-semibold text-blue-700 hover:underline">Inspect →</Link>
                  </td>
                </tr>
              ))}
              {stats.recent.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-10 text-center text-sm text-slate-500">Nothing submitted yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}