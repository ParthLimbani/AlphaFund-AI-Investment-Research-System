"use client";
import { AgentEvent } from "@/lib/api";

const TIMELINE_ROWS: Array<string[]> = [
  ["supervisor"],
  ["fundamental", "technical", "sentiment"],
  ["synthesizer"],
  ["debate"],
  ["risk_manager"],
  ["final_decision"],
  ["reflection"],
];

const LABELS: Record<string, string> = {
  supervisor:     "Supervisor",
  fundamental:    "Fundamental",
  technical:      "Technical",
  sentiment:      "Sentiment",
  synthesizer:    "Synthesizer",
  debate:         "Bull vs Bear",
  risk_manager:   "Risk Manager",
  final_decision: "Final Decision",
  reflection:     "Reflection",
};

const STEP_LABELS: Record<number, string> = {
  0: "01", 1: "02", 2: "03", 3: "04", 4: "05", 5: "06", 6: "07",
};

type NodeStatus = "pending" | "running" | "done";

type Props = { events: AgentEvent[]; activeNode: string | null };

export function AgentTimeline({ events, activeNode }: Props) {
  const done = new Set(events.map((e) => e.node));
  const summaryMap: Record<string, string> = {};
  events.forEach((e) => { if (e.summary) summaryMap[e.node] = e.summary; });

  function status(node: string): NodeStatus {
    if (done.has(node)) return "done";
    if (activeNode === node) return "running";
    return "pending";
  }

  function rowStatus(row: string[]): NodeStatus {
    if (row.every((n) => done.has(n))) return "done";
    if (row.some((n) => done.has(n) || activeNode === n)) return "running";
    return "pending";
  }

  return (
    <div className="flex gap-4">
      {/* Left: step numbers + connecting line */}
      <div className="flex flex-col items-center pt-2.5 shrink-0">
        {TIMELINE_ROWS.map((row, i) => {
          const rs = rowStatus(row);
          return (
            <div key={i} className="flex flex-col items-center">
              <div className={`w-6 h-6 rounded-full border flex items-center justify-center text-[10px] font-mono font-bold transition-all duration-300 ${
                rs === "done"    ? "bg-emerald-500/20 border-emerald-600/50 text-emerald-400" :
                rs === "running" ? "bg-blue-500/20 border-blue-500/60 text-blue-400 animate-pulse" :
                "bg-card border-border/30 text-muted-foreground/30"
              }`}>
                {rs === "done" ? "✓" : STEP_LABELS[i]}
              </div>
              {i < TIMELINE_ROWS.length - 1 && (
                <div className={`w-px flex-1 my-0.5 min-h-[16px] transition-colors duration-500 ${
                  rs === "done" ? "bg-emerald-600/30" : "bg-border/20"
                }`} />
              )}
            </div>
          );
        })}
      </div>

      {/* Right: agent cards */}
      <div className="flex-1 flex flex-col gap-1.5">
        {TIMELINE_ROWS.map((row, i) => (
          <div key={i} className="flex gap-1.5 items-start">
            {row.map((node) => {
              const s = status(node);
              const summary = summaryMap[node];
              return (
                <div key={node} className="flex-1 min-w-0">
                  <div className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border transition-all duration-300 ${
                    s === "done"    ? "border-emerald-800/40 bg-emerald-950/20" :
                    s === "running" ? "border-blue-700/50 bg-blue-950/30 animate-pulse" :
                    "border-border/25 bg-card/30"
                  }`}>
                    <StatusDot status={s} />
                    <span className={`text-xs font-medium truncate ${
                      s === "done"    ? "text-emerald-300/90" :
                      s === "running" ? "text-blue-300" :
                      "text-muted-foreground/40"
                    }`}>
                      {LABELS[node] ?? node}
                    </span>
                  </div>
                  {s === "done" && summary && (
                    <p className="text-[10px] text-muted-foreground/50 px-3 pt-1 truncate leading-tight">
                      {summary}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: NodeStatus }) {
  if (status === "done")    return <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />;
  if (status === "running") return <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0 animate-pulse" />;
  return <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/20 shrink-0" />;
}
