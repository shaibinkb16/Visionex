import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, Send } from "lucide-react";
import { listDocuments, queryDocument } from "../services/api";

const suggestions = ["What is the total?", "When was this?", "Which vendor?"];

function formatDocLabel(doc) {
  const name = doc.filename || "document";
  const short = doc.document_id ? `${doc.document_id.slice(0, 6)}…` : "";
  return `${name} (${short})`;
}

export default function ChatWindow({ selectedDocumentId = "", onSelectDocument = () => {}, refreshToken = null }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [listLoading, setListLoading] = useState(true);
  const bottomRef = useRef();

  const refreshDocuments = useCallback(async () => {
    try { const rows = await listDocuments(80); setDocuments(rows); }
    catch { setDocuments([]); }
    finally { setListLoading(false); }
  }, []);

  useEffect(() => { refreshDocuments(); }, [refreshDocuments]);
  useEffect(() => { if (refreshToken) refreshDocuments(); }, [refreshToken, refreshDocuments]);

  const docOptions = useMemo(() => {
    const map = new Map(documents.map((d) => [d.document_id, d]));
    if (selectedDocumentId && !map.has(selectedDocumentId))
      map.set(selectedDocumentId, { document_id: selectedDocumentId, filename: "Current session" });
    return [...map.values()];
  }, [documents, selectedDocumentId]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const { answer } = await queryDocument(q, selectedDocumentId || undefined);
      setMessages((m) => [...m, { role: "assistant", text: answer }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "Error: " + (e.response?.data?.detail || e.message), error: true }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="rise panel relative flex flex-col overflow-hidden rounded-xl" style={{ minHeight: "360px" }}>
      <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-[#16a34a]/40 to-transparent" />

      {/* Header */}
      <div className="space-y-2.5 border-b border-[#dddbd4] bg-[#efede8] px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-[#dddbd4] bg-white text-[#16a34a]">
              <MessageCircle className="h-3.5 w-3.5" strokeWidth={1.75} />
            </div>
            <div>
              <p className="text-xs font-medium text-[#0a0a0a]">Grounded QA</p>
              <p className="mono text-[10px] uppercase tracking-wider text-[#a0a0a0]">Answers from extracted fields only</p>
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-2.5">
          <label htmlFor="doc-context" className="mono shrink-0 text-[10px] uppercase tracking-wider text-[#a0a0a0]">
            Context
          </label>
          <select id="doc-context" value={selectedDocumentId} onChange={(e) => onSelectDocument(e.target.value)}
            disabled={listLoading || docOptions.length === 0}
            className="input-glow w-full rounded-lg border border-[#dddbd4] bg-white px-2.5 py-1.5 text-xs text-[#0a0a0a] focus:border-[#16a34a]/50 focus:outline-none disabled:opacity-50 sm:max-w-sm"
          >
            {docOptions.length === 0
              ? <option value="">No saved documents</option>
              : docOptions.map((d) => <option key={d.document_id} value={d.document_id}>{formatDocLabel(d)}</option>)
            }
          </select>
        </div>
      </div>

      {/* Messages */}
      <div className="relative flex-1 space-y-2.5 overflow-y-auto bg-[#faf9f6] px-4 py-3">
        <div className="pointer-events-none absolute inset-0 chat-fade" />

        {messages.length === 0 && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            className="flex h-full min-h-[180px] flex-col items-center justify-center gap-3 text-center"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#dddbd4] bg-white text-xl shadow-sm">
              💬
            </div>
            <div className="space-y-0.5">
              <p className="text-xs font-medium text-[#0a0a0a]">Ask about a saved receipt</p>
              <p className="max-w-xs text-[11px] text-[#a0a0a0]">Answers stay grounded in extracted JSON fields.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-1.5">
              {suggestions.map((s) => (
                <button key={s} type="button" onClick={() => setInput(s)}
                  className="rounded-full border border-[#dddbd4] bg-white px-2.5 py-1 text-[11px] text-[#6b6b6b] transition-colors hover:border-[#16a34a]/40 hover:text-[#16a34a]"
                >
                  {s}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div key={i}
              initial={{ opacity: 0, y: 8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div className={[
                "max-w-[80%] rounded-2xl px-3 py-2 text-xs leading-relaxed shadow-sm sm:max-w-sm",
                m.role === "user"
                  ? "rounded-br-sm bg-[#0a0a0a] text-white"
                  : m.error
                    ? "rounded-bl-sm border border-red-200 bg-red-50 text-red-700"
                    : "rounded-bl-sm border border-[#dddbd4] bg-white text-[#0a0a0a]",
              ].join(" ")}>
                {m.text}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
            <div className="flex items-center gap-1 rounded-2xl rounded-bl-sm border border-[#dddbd4] bg-white px-3 py-2.5">
              {[0, 1, 2].map((i) => (
                <motion.span key={i} className="h-1.5 w-1.5 rounded-full bg-[#16a34a]"
                  animate={{ y: [0, -4, 0], opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.12, ease: "easeInOut" }}
                />
              ))}
            </div>
          </motion.div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-[#dddbd4] bg-[#efede8] p-2.5">
        <div className="flex gap-2">
          <input
            className="input-glow flex-1 rounded-lg border border-[#dddbd4] bg-white px-3 py-2 text-xs text-[#0a0a0a] placeholder:text-[#a0a0a0] focus:border-[#16a34a]/50 focus:outline-none"
            placeholder="e.g. What is the total amount?"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={loading}
          />
          <motion.button type="button" onClick={send} disabled={loading || !input.trim()} whileTap={{ scale: 0.97 }}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-[#16a34a] px-3 py-2 text-xs font-medium text-white shadow-sm transition-opacity hover:bg-[#15803d] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Send</span>
          </motion.button>
        </div>
      </div>
    </div>
  );
}
