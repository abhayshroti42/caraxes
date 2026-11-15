import { useCallback, useState } from "react";
import AssetsPanel from "../components/AssetsPanel";
import DocumentsPanel from "../components/DocumentsPanel";
import KnowledgeReview from "../components/KnowledgeReview";

export default function Knowledge() {
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const onProcessed = useCallback(() => setRefreshKey((k) => k + 1), []);

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-8 lg:col-span-1">
        <DocumentsPanel selectedId={selectedDoc} onSelect={setSelectedDoc} onProcessed={onProcessed} />
        <AssetsPanel />
      </div>
      <div className="lg:col-span-2">
        <KnowledgeReview docId={selectedDoc} refreshKey={refreshKey} />
      </div>
    </div>
  );
}