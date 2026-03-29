import { useState, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import UploadForm from "./components/UploadForm";
import ResultView from "./components/ResultView";
import ChatWindow from "./components/ChatWindow";

function AmbientBackdrop() {
  const reduceMotion = useReducedMotion();
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="mesh-blob mesh-blob-a" />
      <div className="mesh-blob mesh-blob-b" />
      <div className="mesh-blob mesh-blob-c" />
      <div className="grid-overlay opacity-[0.35]" />
      {!reduceMotion && <div className="scan-line" />}
    </div>
  );
}

export default function App() {
  const [result, setResult] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState("");
  const reduceMotion = useReducedMotion();
  const showChat = Boolean(result || selectedDocId);

  const resultRef = useRef(null);

  const handleExtractionResult = (next) => {
    setResult(next);
    if (next?.document_id) setSelectedDocId(next.document_id);
    setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
  };

  return (
    <div className="relative min-h-screen flex flex-col">
      <AmbientBackdrop />

      {/* ── Navbar ─────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 border-b border-[#dddbd4] bg-[#f5f4f0]/90 backdrop-blur-md">
        <div className="mx-auto flex h-11 max-w-5xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-black text-[10px] font-bold text-white">
              VX
            </div>
            <span className="text-sm font-semibold tracking-tight text-[#0a0a0a]">Visionex</span>
            <span className="mono hidden rounded-full border border-[#dddbd4] bg-[#efede8] px-2 py-0.5 text-[10px] uppercase tracking-widest text-[#6b6b6b] sm:inline">
              Intelligence
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="mono text-[10px] uppercase tracking-widest text-[#a0a0a0]">
              OCR · NER · LLM
            </span>
            <div className="status-dot" />
          </div>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────────── */}
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6 sm:py-8">

        {/* Hero strip */}
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="hero-shell mb-6 overflow-hidden rounded-2xl border border-white/[0.06] px-5 py-5 sm:px-7 sm:py-6"
        >
          <div className="hero-shine" />
          <div className="relative z-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1.5">
              <p className="mono text-[10px] uppercase tracking-[0.2em] text-[#16a34a]">
                See beyond the scan
              </p>
              <h1 className="text-xl font-semibold tracking-tight text-[#0a0a0a] sm:text-2xl">
                <span className="gradient-text">From messy receipts</span>
                <span className="text-[#0a0a0a]"> to instant intelligence.</span>
              </h1>
              <p className="max-w-lg text-xs leading-relaxed text-[#6b6b6b]">
                Upload a receipt — OCR → LayoutLMv3 NER → LLM fallback → grounded QA. Full pipeline trace included.
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              {["LayoutLMv3", "Groq", "MongoDB"].map((t) => (
                <span
                  key={t}
                  className="mono rounded-full border border-[#dddbd4] bg-[#efede8] px-2.5 py-1 text-[10px] uppercase tracking-wider text-[#6b6b6b]"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Content */}
        <div className="space-y-5">
          <UploadForm
            onResult={handleExtractionResult}
            onSelectHistory={setSelectedDocId}
            selectedDocumentId={selectedDocId}
          />

          {showChat ? (
            <>
              {result ? (
                <motion.div
                  ref={resultRef}
                  initial={reduceMotion ? false : { opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                >
                  <ResultView result={result} />
                </motion.div>
              ) : (
                <div className="rise panel placeholder-tile flex min-h-[100px] items-center justify-center rounded-xl px-6 py-5 text-center">
                  <p className="text-xs text-[#6b6b6b]">
                    History context selected — ask questions below, or upload a new receipt.
                  </p>
                </div>
              )}
              <motion.div
                initial={reduceMotion ? false : { opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
              >
                <ChatWindow
                  selectedDocumentId={selectedDocId}
                  onSelectDocument={setSelectedDocId}
                  refreshToken={result?.document_id}
                />
              </motion.div>
            </>
          ) : (
            <div className="rise panel placeholder-tile flex min-h-[160px] flex-col items-center justify-center gap-3 rounded-xl px-6 py-8 text-center">
              <div className="flex items-center gap-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#dddbd4] bg-[#efede8]">
                  <div className="h-4 w-4 rounded border-2 border-dashed border-[#16a34a]/40" />
                </div>
                <div className="h-8 w-px bg-[#dddbd4]" />
                <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#dddbd4] bg-[#efede8] text-base">
                  💬
                </div>
              </div>
              <p className="text-xs text-[#6b6b6b]">
                Extraction results and grounded QA appear here after upload.
              </p>
            </div>
          )}
        </div>
      </main>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="border-t border-[#dddbd4] py-4">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 sm:px-6">
          <span className="mono text-[10px] text-[#a0a0a0]">
            © {new Date().getFullYear()} Visionex · Document Intelligence
          </span>
          <span className="mono text-[10px] text-[#a0a0a0]">
            LayoutLMv3 · Groq llama-3.3-70b · MongoDB Atlas
          </span>
        </div>
      </footer>
    </div>
  );
}
