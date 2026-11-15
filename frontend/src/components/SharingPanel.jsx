import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { Icon, fmt } from "../lib/ui";

const OPTIONS = [
  { value: "private", title: "Private", icon: "lock", text: "Only your company can see this session." },
  { value: "unlisted", title: "Unlisted", icon: "link", text: "Anyone with the secret link can view it. It is not listed in the gallery." },
  { value: "public", title: "Public", icon: "globe", text: "Listed in the public gallery for anyone to find." },
];

export default function SharingPanel({ submissionId, status, title, onChanged }) {
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");

  const load = useCallback(async () => {
    try {
      setState(await api(`/submissions/${submissionId}/sharing`));
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, [submissionId]);

  // Reload whenever the review status changes: leaving "approved" makes a session private again
  useEffect(() => {
    load();
  }, [load, status]);

  async function change(target) {
    if (!state || busy || target === state.visibility) return;
    if (target !== "private") {
      const audience = target === "public" ? "everyone" : "anyone who has the link";
      const ok = window.confirm(
        `Make this session ${target}?\n\nVisible to ${audience}:\n` +
          `• Title: “${title || "Untitled"}”\n• The content itself\n• Your company name\n\n` +
          "Never shared: brand guidelines, rules, findings, review comments or reviewer names."
      );
      if (!ok) return;
    }
    setBusy(true);
    setError("");
    try {
      setState(await api(`/submissions/${submissionId}/visibility`, { method: "PATCH", body: JSON.stringify({ visibility: target }) }));
      await onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function regenerate() {
    if (!window.confirm("Create a new link? The current link will stop working immediately.")) return;
    setBusy(true);
    setError("");
    try {
      setState(await api(`/submissions/${submissionId}/share-link/regenerate`, { method: "POST" }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function copy(key, url) {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(key);
      setTimeout(() => setCopied(""), 2000);
    } catch {
      /* clipboard unavailable */
    }
  }

  if (!state) return error ? <p className="text-sm text-red-600">{error}</p> : null;

  const origin = window.location.origin;
  const links = [];
  if (state.visibility !== "private" && state.share_token) {
    links.push({
      key: "link",
      label: state.visibility === "unlisted" ? "Shareable link" : "Private share link (also works)",
      url: `${origin}/s/${state.share_token}`,
      regenerate: true,
    });
  }
  if (state.visibility === "public") {
    links.push({ key: "page", label: "Public page", url: `${origin}/gallery/${submissionId}` });
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium text-gray-900">Sharing &amp; visibility</h3>
        {state.published_at && <span className="text-xs text-gray-500">Published {fmt(state.published_at)}</span>}
      </div>

      {!state.can_publish && (
        <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Only approved sessions can be published. If this session's status changes, it automatically returns to private.
        </p>
      )}

      <div className="grid gap-2 sm:grid-cols-3" role="radiogroup">
        {OPTIONS.map((o) => {
          const selected = state.visibility === o.value;
          const disabled = busy || (o.value !== "private" && !state.can_publish);
          return (
            <button
              key={o.value}
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => change(o.value)}
              className={`rounded-lg border p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-50 ${
                selected ? "border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500" : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <span className="flex items-center gap-2 text-sm font-medium text-gray-900">
                <Icon name={o.icon} /> {o.title}
              </span>
              <span className="mt-1 block text-xs text-gray-600">{o.text}</span>
            </button>
          );
        })}
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {links.length > 0 && (
        <div className="mt-4 space-y-3">
          {links.map((l) => (
            <div key={l.key}>
              <div className="mb-1 text-xs font-medium text-gray-500">{l.label}</div>
              <div className="flex gap-2">
                <input readOnly value={l.url} onFocus={(e) => e.target.select()} className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-1.5 text-sm text-gray-700" />
                <button onClick={() => copy(l.key, l.url)} className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50">
                  <Icon name={copied === l.key ? "check" : "copy"} /> {copied === l.key ? "Copied" : "Copy"}
                </button>
                {l.regenerate && (
                  <button onClick={regenerate} disabled={busy} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50">
                    New link
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}