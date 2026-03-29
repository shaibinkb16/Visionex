import { motion } from "framer-motion";
import { FileText, Timer, Cpu, ImageIcon } from "lucide-react";
import PipelineFlow from "./PipelineFlow";
import { documentFileUrl } from "../services/api";

const LABELS = { total_amount: "Total Amount", date: "Date", vendor_name: "Vendor", receipt_id: "Receipt ID" };
const ICONS  = { total_amount: "💰", date: "📅", vendor_name: "🏪", receipt_id: "🧾" };

function ConfidenceBadge({ score }) {
  if (score === null || score === undefined) return null;
  if (score === 0)
    return <span className="rounded-full border border-[#dddbd4] bg-[#efede8] px-1.5 py-0.5 text-[10px] font-medium text-[#6b6b6b]">LLM</span>;
  const pct = Math.round(score * 100);
  const cls = pct >= 75
    ? "border-[#bbf7d0] bg-[#f0fdf4] text-[#16a34a]"
    : "border-orange-200 bg-orange-50 text-orange-600";
  return <span className={`rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${cls}`}>{pct}%</span>;
}

const fieldsContainer = { hidden: {}, show: { transition: { staggerChildren: 0.05, delayChildren: 0.02 } } };
const fieldCard = { hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1] } } };

function DocumentPreview({ documentId, contentType, filename }) {
  const src = documentFileUrl(documentId);
  const isPdf = (contentType && contentType.includes("pdf")) || (filename && filename.toLowerCase().endsWith(".pdf"));
  return (
    <div className="border-b border-[#dddbd4] bg-[#efede8] px-4 py-3">
      <div className="mb-2 flex items-center gap-1.5">
        <ImageIcon className="h-3.5 w-3.5 text-[#16a34a]" strokeWidth={1.75} />
        <p className="mono text-[10px] uppercase tracking-[0.14em] text-[#a0a0a0]">Source document</p>
      </div>
      <div className="overflow-hidden rounded-lg border border-[#dddbd4] bg-white">
        {isPdf
          ? <iframe title={filename || "PDF"} src={src} className="h-[min(320px,45vh)] w-full bg-white" />
          : <img src={src} alt={filename || "Receipt"} className="mx-auto max-h-[min(320px,45vh)] w-full object-contain" />
        }
      </div>
      <p className="mono mt-1.5 truncate text-center text-[10px] text-[#a0a0a0]">{filename}</p>
    </div>
  );
}

export default function ResultView({ result }) {
  if (!result) return null;
  const { document_id, content_type, extracted, confidence, extraction_method, processing_time_ms, filename, pipeline_trace = [] } = result;
  const traceData = pipeline_trace.length ? pipeline_trace : [
    { stage: "sanitize", status: "done", detail: "Input sanitized" },
    { stage: "ner",      status: "done", detail: "NER inference executed" },
    { stage: "finalize", status: "done", detail: "Output assembled" },
  ];

  return (
    <div className="rise panel relative flex flex-col overflow-hidden rounded-xl">
      {/* green top accent line */}
      <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-[#16a34a]/50 to-transparent" />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#dddbd4] bg-[#efede8] px-4 py-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-[#dddbd4] bg-white text-[#16a34a]">
            <FileText className="h-3.5 w-3.5" strokeWidth={1.75} />
          </div>
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-[#0a0a0a]">{filename}</p>
            <p className="mono text-[10px] uppercase tracking-wider text-[#a0a0a0]">Extracted document</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
            extraction_method === "ner"
              ? "border border-[#bbf7d0] bg-[#f0fdf4] text-[#16a34a]"
              : "border border-[#dddbd4] bg-white text-[#6b6b6b]"
          }`}>
            <Cpu className="h-2.5 w-2.5 opacity-80" />
            {extraction_method}
          </span>
          <span className="mono flex items-center gap-1 rounded-full border border-[#dddbd4] bg-white px-2 py-0.5 text-[10px] text-[#6b6b6b]">
            <Timer className="h-2.5 w-2.5" />{processing_time_ms} ms
          </span>
        </div>
      </div>

      {/* Preview */}
      {document_id && <DocumentPreview documentId={document_id} contentType={content_type} filename={filename} />}

      {/* Pipeline trace — directly below image */}
      <div className="border-b border-[#dddbd4] bg-[#faf9f6] px-4 py-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <p className="mono text-[10px] uppercase tracking-[0.14em] text-[#a0a0a0]">Layer 1 · Pipeline trace</p>
          <span className="rounded-full border border-[#bbf7d0] bg-[#f0fdf4] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[#16a34a]">
            Trace
          </span>
        </div>
        <PipelineFlow steps={traceData} isLoading={false} />
      </div>

      {/* Fields */}
      <div>
        <div className="px-4 py-2.5">
          <p className="mono text-[10px] uppercase tracking-[0.14em] text-[#a0a0a0]">Layer 2 · Structured fields</p>
        </div>
        <motion.div className="grid grid-cols-2 gap-px bg-[#dddbd4] sm:grid-cols-4"
          initial="hidden" animate="show" variants={fieldsContainer}
        >
          {Object.entries(LABELS).map(([key, label]) => (
            <motion.div key={key} variants={fieldCard}
              className="bg-[#faf9f6] px-4 py-3 transition-colors hover:bg-[#f0fdf4]/50"
            >
              <div className="mb-1.5 flex items-center gap-1.5">
                <span className="text-sm leading-none">{ICONS[key]}</span>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[#a0a0a0]">{label}</p>
              </div>
              <div className="flex items-end justify-between gap-1">
                <p className="truncate text-xs font-semibold text-[#0a0a0a]">
                  {extracted[key] || <span className="font-normal italic text-[#a0a0a0]">—</span>}
                </p>
                <ConfidenceBadge score={confidence[key]} />
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
