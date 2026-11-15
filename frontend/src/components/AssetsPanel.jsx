import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";

export default function AssetsPanel() {
  const [assets, setAssets] = useState([]);
  const [name, setName] = useState("");
  const [type, setType] = useState("logo");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setAssets(await api("/brand-assets"));
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function upload(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!name.trim()) {
      setError("Enter a name for the asset first.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const form = new FormData();
      form.append("asset_type", type);
      form.append("name", name.trim());
      form.append("file", file);
      await api("/brand-assets", { method: "POST", body: form });
      setName("");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-gray-800">Approved logos and images</h2>
      <div className="space-y-2 rounded-lg border border-gray-200 bg-white p-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Asset name"
          className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <div className="flex items-center gap-2">
          <select value={type} onChange={(e) => setType(e.target.value)} className="rounded border border-gray-300 px-2 py-1 text-sm">
            <option value="logo">Logo</option>
            <option value="image">Image</option>
          </select>
          <label className="cursor-pointer rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700">
            {busy ? "Uploading…" : "Choose file"}
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={upload} disabled={busy} className="hidden" />
          </label>
        </div>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <ul className="mt-3 space-y-1 text-sm text-gray-700">
        {assets.map((a) => (
          <li key={a.id} className="rounded border border-gray-200 bg-white px-3 py-1.5">
            {a.name} <span className="text-xs text-gray-500">({a.asset_type}, {a.metadata?.width}×{a.metadata?.height})</span>
          </li>
        ))}
        {assets.length === 0 && <li className="text-gray-500">No assets yet. Upload your logo so logo checks can run.</li>}
      </ul>
    </div>
  );
}