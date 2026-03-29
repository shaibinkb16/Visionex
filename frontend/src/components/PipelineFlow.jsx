import { motion, useReducedMotion } from "framer-motion";
import { Check, Loader2, Circle, AlertCircle } from "lucide-react";
import { getStageMeta } from "../lib/stageMeta";

function frontierIndex(steps, isLoading) {
  if (!isLoading || !steps.length) return -1;
  const errIdx = steps.findIndex((s) => s.status === "error");
  if (errIdx >= 0) return errIdx;
  const active = steps.findIndex((s) => s.status !== "done" && s.status !== "skipped" && s.status !== "error");
  if (active >= 0) return active;
  return steps.length - 1;
}

function normalizeStatus(step, isFrontier) {
  if (step.status === "pending") return "pending";
  if (step.status === "error")   return "error";
  if (step.status === "done" || step.status === "skipped") return "done";
  if (step.status === "running" || isFrontier) return "running";
  return "running";
}

function StatusIcon({ status, isFrontier, reduceMotion }) {
  if (status === "error")
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-100 text-red-600 ring-1 ring-red-200">
        <AlertCircle className="h-3.5 w-3.5" />
      </span>
    );
  if (status === "done")
    return (
      <motion.span
        initial={reduceMotion ? false : { scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="flex h-6 w-6 items-center justify-center rounded-full bg-[#f0fdf4] text-[#16a34a] ring-1 ring-[#bbf7d0]"
      >
        <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
      </motion.span>
    );
  if (status === "pending")
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-dashed border-[#dddbd4] bg-[#efede8] text-[#a0a0a0]">
        <Circle className="h-1.5 w-1.5 fill-[#a0a0a0]" />
      </span>
    );
  // running
  return (
    <span className={`flex h-6 w-6 items-center justify-center rounded-full bg-[#f0fdf4] text-[#16a34a] ring-1 ring-[#16a34a]/40 ${
      isFrontier ? "shadow-[0_0_12px_-2px_rgba(22,163,74,0.4)]" : ""
    }`}>
      <Loader2 className={`h-3.5 w-3.5 ${isFrontier && !reduceMotion ? "animate-spin" : ""}`} />
    </span>
  );
}

function Connector({ active, reduceMotion }) {
  return (
    <div className="relative mx-1 flex h-8 min-w-[20px] max-w-[32px] flex-1 items-center">
      <div className="h-[1.5px] w-full rounded-full bg-[#dddbd4]" />
      <motion.div
        className="absolute left-0 h-[1.5px] rounded-full bg-[#16a34a]"
        initial={false}
        animate={
          reduceMotion
            ? { width: active ? "100%" : "30%" }
            : {
                width: active ? ["35%", "100%", "60%", "100%"] : "30%",
                opacity: active ? [0.5, 1, 0.7, 1] : 0.3,
              }
        }
        transition={
          reduceMotion
            ? { duration: 0.2 }
            : { duration: active ? 2.2 : 0.3, repeat: active ? Infinity : 0, ease: "easeInOut" }
        }
        style={{ top: "50%", transform: "translateY(-50%)" }}
      />
    </div>
  );
}

export default function PipelineFlow({ steps = [], isLoading = false, className = "" }) {
  const reduceMotion = useReducedMotion();

  const list = steps.length
    ? steps
    : isLoading
      ? [
          { stage: "receive",  status: "running", detail: "Waiting for upload…" },
          { stage: "ocr",      status: "pending", detail: "Queued" },
          { stage: "ner",      status: "pending", detail: "Queued" },
          { stage: "persist",  status: "pending", detail: "Queued" },
        ]
      : [];

  const fIdx = frontierIndex(list, isLoading);

  const variants = {
    hidden: { opacity: 0 },
    show:   { opacity: 1, transition: { staggerChildren: reduceMotion ? 0 : 0.06, delayChildren: 0.02 } },
  };
  const item = {
    hidden: { opacity: 0, y: reduceMotion ? 0 : 8 },
    show:   { opacity: 1, y: 0, transition: { type: "spring", stiffness: 400, damping: 30 } },
  };

  if (!list.length) return null;

  return (
    <div className={`w-full ${className}`}>
      <div className="overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <motion.div
          className="flex min-w-min items-stretch px-0.5"
          variants={variants}
          initial="hidden"
          animate="show"
          key={list.map((s) => `${s.stage}-${s.status}`).join("|")}
        >
          {list.map((step, idx) => {
            const { label, Icon } = getStageMeta(step.stage);
            const isFrontier = idx === fIdx;
            const err  = step.status === "error";
            const done = step.status === "done" || step.status === "skipped";
            const visStatus = normalizeStatus(step, isFrontier);

            return (
              <motion.div key={`${step.stage}-${idx}`} variants={item} className="flex items-stretch">
                <div className={[
                  "group relative w-[176px] shrink-0 overflow-hidden rounded-xl border px-3 py-2.5 sm:w-[196px]",
                  err  ? "border-red-200 bg-red-50"
                       : done
                         ? "border-[#bbf7d0] bg-[#f0fdf4]"
                         : isFrontier
                           ? "border-[#16a34a]/40 bg-[#f0fdf4]/60 shadow-[0_0_0_1px_rgba(22,163,74,0.08),0_4px_16px_-4px_rgba(22,163,74,0.15)]"
                           : "border-[#dddbd4] bg-[#faf9f6]",
                ].join(" ")}>
                  {/* active pulse overlay */}
                  {isFrontier && !err && !reduceMotion && (
                    <motion.div
                      className="pointer-events-none absolute inset-0 rounded-xl bg-[#16a34a]/5"
                      animate={{ opacity: [0.3, 0.8, 0.3] }}
                      transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
                    />
                  )}

                  <div className="relative flex items-start gap-2.5">
                    {/* stage icon */}
                    <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${
                      done ? "border-[#bbf7d0] bg-[#f0fdf4] text-[#16a34a]"
                           : isFrontier ? "border-[#16a34a]/30 bg-white text-[#16a34a]"
                           : "border-[#dddbd4] bg-white text-[#6b6b6b]"
                    }`}>
                      <Icon className="h-4 w-4" strokeWidth={1.75} />
                    </div>

                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center justify-between gap-1.5">
                        <p className={`truncate text-[10px] font-semibold uppercase tracking-[0.1em] ${
                          done ? "text-[#16a34a]" : isFrontier ? "text-[#16a34a]" : "text-[#6b6b6b]"
                        }`}>
                          {label}
                        </p>
                        <StatusIcon status={visStatus} isFrontier={isFrontier} reduceMotion={reduceMotion} />
                      </div>
                      <p className="line-clamp-2 text-[10px] leading-relaxed text-[#6b6b6b]">
                        {step.detail || "—"}
                      </p>
                      {typeof step.elapsed_ms === "number" && (
                        <p className="mono text-[10px] text-[#a0a0a0]">{step.elapsed_ms} ms</p>
                      )}
                    </div>
                  </div>
                </div>

                {idx < list.length - 1 && <Connector active={isLoading} reduceMotion={reduceMotion} />}
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </div>
  );
}
