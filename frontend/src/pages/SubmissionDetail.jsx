import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { FindingsList, ImageOverlay, TextHighlighter } from "../components/Results";
import SharingPanel from "../components/SharingPanel";
import { CorrectionPanel, HistoryPanel, ReviewPanel } from "../components/Workflow";
import { api } from "../lib/api";
import { ENGINE, Icon, StatusBadge, VisibilityBadge, label } from "../lib/ui";

export default function SubmissionDetail() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();

  const [sub, setSub] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [fileUrl, setFileUrl] = useState("");
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [active, setActive] = useState(null);
  const [historyKey, setHistoryKey] = useState(0);
  const autoStarted = useRef(false);

  const loadSub = useCallback(async () => setSub(await api(`/submissions/${id}`)), [id]);

  const runAnalysis = useCallback(async () => {
    setError("");
    setRunning(true);
    try {
      setAnalysis(await api(`/submissions/${id}/analyze`, { method: "POST" }));
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
      await loadSub();
      setHistoryKey((k) => k + 1);
    }
  }, [id, loadSub]);

  // Load the submission, its latest analysis and its file
  useEffect(() => {
    (async () => {
      try {
        const s = await api(`/submissions/${id}`);
        setSub(s);
        if (s.content_type !== "text") setFileUrl((await api(`/submissions/${id}/file-url`)).url);
        try {
          setAnalysis(await api(`/submissions/${id}/analysis`));
        } catch {
          setAnalysis(null); // no completed analysis yet
        }
      } catch (e) {
        setError(e.message);
      }
    })();
  }, [id]);

  // After "Run Pre-Publication Check", start the analysis once
  useEffect(() => {
    if (params.get("auto") === "1" && !autoStarted.current) {
      autoStarted.current = true;
      setParams({}, { replace: true });
      runAnalysis();
    }
  }, [params, setParams, runAnalysis]);

  async function applyCorrection(text) {
    setBusy(true);
    setError("");
    try {
      await api(`/submissions/${id}/revise`, { method: "POST", body: JSON.stringify({ text_content: text }) });
      await loadSub();
      setActive(null);
      await runAnalysis();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function review(decision, comment) {
    setBusy(true);
    setError("");
    try {
      await api(`/submissions/${id}/review`, { method: "POST", body: JSON.stringify({ decision, comment }) });
      await loadSub();
      setHistoryKey((k) => k + 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function setFindingStatus(findingId, status) {
    try {
      await api(`/findings/${findingId}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setAnalysis((a) => ({ ...a, findings: a.findings.map((f) => (f.id === findingId ? { ...f, status } : f)) }));
    } catch (e) {
      setError(e.message);
    }
  }

  if (!sub) return <p className="text-sm text-slate-500">{error || "Loading…"}</p>;

  const findings = analysis?.findings ?? [];
  const summary = analysis?.summary ?? {};
  const openCount = findings.filter((f) => f.status === "open").length;
  const isText = sub.content_type === "text";
  const textToShow = summary.analyzed_text ?? sub.text_content ?? "";
  const canReview = sub.status === "in_review";
  const canPublish = true;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <Link to="/queue" className="hover:text-slate-900">← Back</Link>
            <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono">ID #{String(sub.id).slice(0, 6)}</span>
            <StatusBadge value={sub.status} />
            <VisibilityBadge value={sub.visibility} />
            <span>• Author: <span className="font-semibold text-slate-800">{sub.created_by_name || "unknown"}</span></span>
            <span>• v{sub.current_version}</span>
          </div>
          <h2 className="mt-2 text-2xl font-bold text-slate-900">{sub.title || "Untitled"}</h2>
        </div>
        <button
          onClick={runAnalysis}
          disabled={running}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-50"
        >
          <Icon name="shield" /> {analysis ? "Re-check" : "Run analysis"}
        </button>
      </div>

      {error && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {running && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Analysing against your brand guidelines. This can take up to a minute…
        </p>
      )}

      {analysis && (
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="space-y-6 lg:col-span-3">
            <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-3">
                <div className="text-sm font-semibold text-slate-900">
                  Live Document Canvas <span className="font-normal text-slate-500">({sub.content_type})</span>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-600">
                  {Object.values(ENGINE).map((e) => (
                    <span key={e.name} className="inline-flex items-center gap-1">
                      <span className={`h-2.5 w-2.5 rounded-sm ${e.mark.split(" ")[0]}`} /> {e.name}
                    </span>
                  ))}
                  <span className="inline-flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm bg-emerald-200" /> Accepted</span>
                </div>
              </div>
              {sub.content_type === "pdf" && fileUrl && (
                <a href={fileUrl} target="_blank" rel="noreferrer" className="block px-5 pt-3 text-xs text-blue-700 hover:underline">
                  Open the original PDF
                </a>
              )}
              {sub.content_type === "image" ? (
                fileUrl && <ImageOverlay url={fileUrl} findings={findings} active={active} onSelect={setActive} />
              ) : (
                <TextHighlighter text={textToShow} findings={findings} active={active} onSelect={setActive} />
              )}
              <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
                <span className="font-semibold text-slate-800">{summary.total ?? 0} finding{summary.total === 1 ? "" : "s"}</span>
                {summary.truncated && <span className="text-amber-700">Only the first part of the PDF text was checked.</span>}
                {summary.checks && (
                  <details>
                    <summary className="cursor-pointer">Automatic checks</summary>
                    <ul className="mt-1">
                      {Object.entries(summary.checks).map(([k, v]) => <li key={k}>{label(k)}: {v}</li>)}
                    </ul>
                  </details>
                )}
              </div>
            </section>

            {isText && (
              <CorrectionPanel summary={summary} originalText={textToShow} onApply={applyCorrection} busy={busy || running} />
            )}
            {sub.content_type === "pdf" && (
              <p className="text-sm text-slate-600">For PDFs, fix the content in your source file and upload it as a new submission.</p>
            )}
            {sub.content_type === "image" && (
              <p className="text-sm text-slate-600">For images, apply the suggested fixes in your design tool and upload a new version as a new submission.</p>
            )}

            {canReview && <ReviewPanel onReview={review} busy={busy} />}
            {canPublish && <SharingPanel submissionId={id} status={sub.status} title={sub.title} onChanged={loadSub} />}
            <HistoryPanel id={id} refreshKey={historyKey} />
          </div>

          <aside className="lg:col-span-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:sticky lg:top-24 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">Pre-Publication Findings ({openCount} open)</h3>
                <span className="text-xs text-slate-400">{findings.length} total</span>
              </div>
              <FindingsList findings={findings} active={active} onSelect={setActive} onStatus={setFindingStatus} />
            </div>
          </aside>
        </div>
      )}

      {!analysis && !running && (
        <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">
          No analysis yet. Click “Run analysis” to check this content against your brand guidelines.
          {canReview && <div className="mt-6 text-left"><ReviewPanel onReview={review} busy={busy} /></div>}
        </div>
      )}
    </div>
  );
}