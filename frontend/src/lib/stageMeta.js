import {
  Inbox,
  FileText,
  ScanLine,
  Sparkles,
  Cpu,
  GitBranch,
  Database,
  CheckCircle2,
  AlertCircle,
  Layers,
  Wand2,
  Shield,
} from "lucide-react";

/** Human-readable labels for backend pipeline stage keys */
const LABELS = {
  receive: "Receive",
  read: "Read",
  ocr: "OCR",
  sanitize: "Sanitize",
  ner: "Layout NER",
  threshold_gate: "Confidence",
  rule_fallback: "Rules",
  ner_rescue: "NER Rescue",
  llm_groq: "Groq",
  llm_gemini: "Gemini",
  finalize: "Finalize",
  persist: "Persist",
  complete: "Complete",
  error: "Error",
  unknown: "Stage",
};

const ICONS = {
  receive: Inbox,
  read: FileText,
  ocr: ScanLine,
  sanitize: Sparkles,
  ner: Cpu,
  threshold_gate: Shield,
  rule_fallback: Layers,
  ner_rescue: Cpu,
  llm_groq: Wand2,
  llm_gemini: Wand2,
  finalize: CheckCircle2,
  persist: Database,
  complete: CheckCircle2,
  error: AlertCircle,
};

const ACCENTS = {
  receive: "cyan",
  read: "sky",
  ocr: "violet",
  sanitize: "fuchsia",
  ner: "emerald",
  persist: "amber",
  complete: "emerald",
  error: "rose",
};

function titleCase(s) {
  return s
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getStageMeta(stage) {
  const key = (stage || "unknown").toLowerCase();
  const Icon = ICONS[key] || GitBranch;
  const label = LABELS[key] || titleCase(stage || "stage");
  const accent = ACCENTS[key] || "slate";
  return { label, Icon, accent, key };
}

export { LABELS };
