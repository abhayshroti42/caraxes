import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

const STATUS_STYLES = {
  uploaded: "bg-gray-100 text-gray-700",
  processing: "bg-amber-100 text-amber-800",
  extracted: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function DocumentsPanel({ selectedId, onSelect, onProcessed }) {
  const [docs, setDocs] = useState([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const prevStatus = useRef({});

  const load = useCallback(async () => {
    try {
      const data = await api("/brand-documents");
      // When a document finishes processing, tell the review panel to reload
      data.forEach((d) => {
        if (prevStatus.current[d.id] === "processing" && d.status === "extracted") onProcessed();
      });
      prevStatus.current = Object.fromEntries(data.map((d) => [d.id, d.status]));
      setDocs(data);
    } catch (e) {
      setError(e.message);
    }
  }, [onProcessed]);

  useEffect(() => {
    load();
  }, [load]);

  // While anything is processing, check again every 3 seconds
  const anyProcessing = docs.some((d) => d.status === "processing");
  useEffect(() => {
    if (!anyProcessing) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [anyProcessing, load]);

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const doc = await api("/brand-documents", { method: "POST", body: form });
      await api(`/brand-documents/${doc.id}/extract`, { method: "POST" });
      onSelect(doc.id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function reextract(id) {
    setError("");
    try {
      await api(`/brand-documents/${id}/extract?force=true`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function openPdf(id) {
    const win = window.open("", "_blank"); // open first so the popup isn't blocked
    try {
      const res = await api(`/brand-documents/${id}/url`);
      win.location = res.url;
    } catch (err) {
      win?.close();
      setError(err.message);
    }
  }

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-gray-800">Brand guideline documents</h2>

      <label className="block cursor-pointer rounded-lg border-2 border-dashed border-gray-300 bg-white px-4 py-6 text-center text-sm text-gray-600 hover:border-indigo-400">
        {uploading ? "Uploading…" : "Click to upload a guidelines PDF"}
        <input type="file" accept="application/pdf" onChange={handleUpload} disabled={uploading} className="hidden" />
      </label>

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      <ul className="mt-4 space-y-2">
        {docs.map((d) => (
          <li
            key={d.id}
            onClick={() => onSelect(d.id)}
            className={`cursor-pointer rounded-lg border bg-white px-3 py-3 ${
              selectedId === d.id ? "border-indigo-500 ring-1 ring-indigo-500" : "border-gray-200"
            }`}
          >
            <div className="truncate text-sm font-medium text-gray-900">{d.filename}</div>
            <div className="mt-1 flex items-center justify-between">
              <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[d.status]}`}>
                {d.status === "processing" ? "processing…" : d.status}
              </span>
              <span className="text-xs text-gray-500">{d.page_count} pages</span>
            </div>
            {d.status === "failed" && d.error_message && (
              <p className="mt-1 break-words text-xs text-red-600">{d.error_message}</p>
            )}
            <div className="mt-2 flex gap-3 text-xs">
              <button
                onClick={(e) => { e.stopPropagation(); openPdf(d.id); }}
                className="text-indigo-600 hover:underline"
              >
                View PDF
              </button>
              {d.status !== "processing" && (
                <button
                  onClick={(e) => { e.stopPropagation(); reextract(d.id); }}
                  className="text-gray-600 hover:underline"
                >
                  Re-extract
                </button>
              )}
            </div>
          </li>
        ))}
        {docs.length === 0 && <li className="text-sm text-gray-500">No documents yet.</li>}
      </ul>
    </div>
  );
}