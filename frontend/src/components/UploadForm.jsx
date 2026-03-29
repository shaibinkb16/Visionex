import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Sparkles, FileType, RefreshCw } from "lucide-react";
import { extractDocument, getExtractionStatus, listDocuments } from "../services/api";
import PipelineFlow from "./PipelineFlow";

function formatWhen(value) {
  if (!value) return "—";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "—";
  return dt.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}

export default function UploadForm({ onResult, onSelectHistory = () => {}, selectedDocumentId = "" }) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [liveSteps, setLiveSteps] = useState([]);
  const [stagingPreview, setStagingPreview] = useState({ url: null, kind: null });
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const inputRef = useRef();

  const refreshHistory = async () => {
    try {
      const docs = await listDocuments(8);
      const rows = Array.isArray(docs) ? docs : [];
      rows.sort((a, b) => new Date(b?.created_at || 0) - new Date(a?.created_at || 0));
      setHistory(rows);
    } catch { setHistory([]); }
    finally { setHistoryLoading(false); }
  };

  useEffect(() => { refreshHistory(); }, []);
  useEffect(() => () => { if (stagingPreview.url) URL.revokeObjectURL(stagingPreview.url); }, [stagingPreview.url]);

  const handle = async (file) => {
    if (!file) return;
    setError(""); setLoading(true); setLiveSteps([]);
    if (stagingPreview.url) URL.revokeObjectURL(stagingPreview.url);
    const kind = file.type === "application/pdf" ? "pdf" : file.type.startsWith("image/") ? "image" : null;
    const url = kind ? URL.createObjectURL(file) : null;
    setStagingPreview({ url, kind });
    const requestId = globalThis.crypto?.randomUUID?.() || `req-${Date.now()}`;
    const pollTimer = setInterval(async () => {
      try { const s = await getExtractionStatus(requestId); if (s?.steps) setLiveSteps(s.steps); } catch {}
    }, 400);
    try {
      const result = await extractDocument(file, requestId);
      if (result?.pipeline_trace?.length) setLiveSteps(result.pipeline_trace);
      onResult(result);
      await refreshHistory();
    } catch (e) {
      setError(e.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      clearInterval(pollTimer); setLoading(false);
      if (url) URL.revokeObjectURL(url);
      setStagingPreview({ url: null, kind: null });
    }
  };

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="mono text-[10px] uppercase tracking-[0.18em] text-[#a0a0a0]">Ingest</p>
          <h2 className="text-sm font-semibold text-[#0a0a0a]">Document upload</h2>
        </div>
        {loading && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-1.5 rounded-full border border-[#bbf7d0] bg-[#f0fdf4] px-2.5 py-1"
          >
            <Sparkles className="h-3 w-3 text-[#16a34a]" />
            <span className="mono text-[10px] font-medium uppercase tracking-wider text-[#16a34a]">Pipeline active</span>
          </motion.div>
        )}
      </div>

      {/* Drop zone */}
      <motion.div
        layout
        className={[
          "upload-shell relative overflow-hidden rounded-xl border-2 border-dashed transition-colors duration-200",
          loading
            ? "cursor-wait border-[#16a34a]/40 bg-[#f0fdf4]"
            : dragging
              ? "cursor-copy border-[#16a34a]/60 bg-[#f0fdf4]"
              : "cursor-pointer border-[#dddbd4] bg-[#faf9f6] hover:border-[#16a34a]/40 hover:bg-[#f0fdf4]/60",
        ].join(" ")}
        onClick={() => !loading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handle(e.dataTransfer.files[0]); }}
      >
        <div className="pointer-events-none absolute inset-0 upload-grid opacity-60" />
        {!loading && !dragging && <div className="pointer-events-none absolute inset-0 upload-shimmer" />}

        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp,application/pdf"
          className="hidden" onChange={(e) => handle(e.target.files?.[0])} />

        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="relative z-10 flex min-h-[260px] flex-col gap-4 px-4 py-5 lg:flex-row lg:items-start lg:px-6"
            >
              {stagingPreview.url && (
                <div className="mx-auto w-full max-w-[200px] shrink-0 overflow-hidden rounded-lg border border-[#dddbd4] bg-white lg:mx-0">
                  {stagingPreview.kind === "pdf" ? (
                    <div className="flex flex-col items-center gap-1.5 py-5">
                      <FileType className="h-7 w-7 text-[#16a34a]/60" strokeWidth={1.25} />
                      <p className="mono text-[10px] text-[#a0a0a0]">PDF processing</p>
                    </div>
                  ) : (
                    <img src={stagingPreview.url} alt="" className="max-h-40 w-full object-contain" />
                  )}
                </div>
              )}
              <div className="min-w-0 flex-1 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="relative flex h-9 w-9 shrink-0 items-center justify-center">
                    <span className="pipeline-orbit" />
                    <span className="relative flex h-7 w-7 items-center justify-center rounded-lg border border-[#bbf7d0] bg-[#f0fdf4] text-[#16a34a]">
                      <Upload className="h-3.5 w-3.5" />
                    </span>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[#0a0a0a]">Processing pipeline</p>
                    <p className="text-xs text-[#6b6b6b]">Stages update live as work completes.</p>
                  </div>
                </div>
                <PipelineFlow steps={liveSteps} isLoading />
              </div>
            </motion.div>
          ) : (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="relative z-10 flex min-h-[180px] flex-col items-center justify-center gap-3 px-6 py-8 text-center"
            >
              <motion.div
                className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#dddbd4] bg-white shadow-sm"
                whileHover={{ scale: 1.05, y: -1 }}
                transition={{ type: "spring", stiffness: 400, damping: 22 }}
              >
                <Upload className="h-5 w-5 text-[#16a34a]" strokeWidth={1.75} />
              </motion.div>
              <div className="space-y-0.5">
                <p className="text-sm font-semibold text-[#0a0a0a]">
                  {dragging ? "Drop to ingest" : "Drag & drop or click to upload"}
                </p>
                <p className="text-xs text-[#a0a0a0]">JPEG · PNG · WebP · PDF</p>
              </div>
              <p className="mono max-w-sm text-[10px] text-[#a0a0a0]">
                OCR → LayoutLMv3 NER → LLM fallback pipeline
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* History */}
      <div className="rise panel overflow-hidden rounded-xl">
        <div className="flex items-center justify-between gap-2 border-b border-[#dddbd4] bg-[#efede8] px-4 py-2.5">
          <div>
            <p className="mono text-[10px] uppercase tracking-[0.16em] text-[#a0a0a0]">History</p>
            <p className="text-xs font-medium text-[#0a0a0a]">Previous uploads</p>
          </div>
          <button type="button" onClick={refreshHistory}
            className="flex items-center gap-1.5 rounded-lg border border-[#dddbd4] bg-white px-2 py-1 text-[10px] text-[#6b6b6b] transition-colors hover:border-[#16a34a]/40 hover:text-[#16a34a]"
          >
            <RefreshCw className="h-3 w-3" />Refresh
          </button>
        </div>
        <div className="max-h-[180px] overflow-y-auto px-3 py-2.5">
          {historyLoading ? (
            <p className="py-1 text-xs text-[#a0a0a0]">Loading…</p>
          ) : history.length === 0 ? (
            <p className="py-1 text-xs text-[#a0a0a0]">No previous uploads yet.</p>
          ) : (
            <div className="space-y-1.5">
              {history.map((doc) => {
                const active = selectedDocumentId && doc.document_id === selectedDocumentId;
                return (
                  <button key={doc.document_id} type="button" onClick={() => onSelectHistory(doc.document_id)}
                    className={["w-full rounded-lg border px-3 py-2 text-left transition-colors",
                      active ? "border-[#16a34a]/40 bg-[#f0fdf4]"
                             : "border-[#dddbd4] bg-[#faf9f6] hover:border-[#16a34a]/30 hover:bg-[#f0fdf4]/60",
                    ].join(" ")}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="line-clamp-1 text-xs font-medium text-[#0a0a0a]">{doc.filename || "Untitled"}</p>
                      <span className="mono shrink-0 text-[10px] uppercase tracking-wider text-[#a0a0a0]">
                        {doc.extraction_method || "—"}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[10px] text-[#a0a0a0]">{formatWhen(doc.created_at)}</p>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
