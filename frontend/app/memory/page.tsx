"use client";
import { useEffect, useState } from "react";
import { getMemory, Belief } from "@/lib/api";

const AGENT_COLORS: Record<string, string> = {
  fundamental: "border-blue-700/40 bg-blue-950/20 text-blue-300/70",
  technical:   "border-violet-700/40 bg-violet-950/20 text-violet-300/70",
  sentiment:   "border-amber-700/40 bg-amber-950/20 text-amber-300/70",
  synthesizer: "border-emerald-700/40 bg-emerald-950/20 text-emerald-300/70",
  risk:        "border-red-700/40 bg-red-950/20 text-red-300/70",
};

export default function MemoryPage() {
  const [beliefs, setBeliefs] = useState<Belief[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMemory().then((b) => { setBeliefs(b); setLoading(false); });
  }, []);

  return (
    <div className="max-w-3xl mx-auto w-full px-4 py-8 space-y-6">

      {/* Header */}
      <div className="border-b border-border/30 pb-4">
        <h2 className="text-lg font-bold tracking-tight">System Memory</h2>
        <p className="text-xs text-muted-foreground/55 mt-1 max-w-lg leading-relaxed">
          Investment beliefs extracted via CVRF (Conceptual Verbal Reinforcement) from past decision cycles.
          These beliefs are injected into each agent at the start of the next run.
        </p>
      </div>

      {loading && (
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span className="w-3 h-3 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
          Loading memory…
        </div>
      )}

      {!loading && beliefs.length === 0 && (
        <div className="rounded-xl border border-border/30 bg-card/30 p-12 text-center space-y-3">
          <div className="text-3xl opacity-20">🧠</div>
          <p className="text-sm text-muted-foreground">No beliefs extracted yet.</p>
          <p className="text-xs text-muted-foreground/50">
            Run analyses multiple times for the same ticker to build memory.
          </p>
        </div>
      )}

      {!loading && beliefs.length > 0 && (
        <div className="space-y-2.5">
          {beliefs.map((b, i) => (
            <div key={i} className="rounded-lg border border-border/35 bg-card/30 hover:bg-card/50 transition-colors overflow-hidden">
              <div className="px-4 py-3 flex gap-3">
                <span className="text-muted-foreground/30 font-mono text-xs mt-0.5 shrink-0">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground/85 leading-relaxed">{b.belief}</p>

                  <div className="flex items-center gap-2 mt-2.5 flex-wrap">
                    {b.relevant_agents?.map((a) => (
                      <span
                        key={a}
                        className={`text-[9px] px-2 py-0.5 rounded border font-semibold tracking-wider uppercase ${
                          AGENT_COLORS[a] ?? "border-border/40 bg-muted/20 text-muted-foreground/50"
                        }`}
                      >
                        {a}
                      </span>
                    ))}
                    <div className="ml-auto flex items-center gap-3">
                      {b.ticker && (
                        <span className="text-[10px] font-mono text-muted-foreground/50 border border-border/30 px-2 py-0.5 rounded">
                          {b.ticker}
                        </span>
                      )}
                      <span className="text-[10px] font-mono text-muted-foreground/35">
                        {b.created_at?.slice(0, 10)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
