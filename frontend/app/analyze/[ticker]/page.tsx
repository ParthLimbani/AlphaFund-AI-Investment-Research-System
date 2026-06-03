"use client";
import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import { startAnalysis, subscribeToStream, getResult, AgentEvent } from "@/lib/api";
import { AgentTimeline } from "@/components/AgentTimeline";
import { VerdictCard } from "@/components/VerdictCard";
import { DebateView } from "@/components/DebateView";
import { ResearchTabs } from "@/components/ResearchTabs";
import { RiskMeter } from "@/components/RiskMeter";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Link from "next/link";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FinalData = Record<string, any>;

export default function AnalyzePage() {
  const { ticker } = useParams<{ ticker: string }>();
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [activeNode, setActiveNode] = useState<string | null>("supervisor");
  const [finalData, setFinalData] = useState<FinalData | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const sessionRef = useRef<string | null>(null);
  const unsubRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!ticker || status !== "idle") return;
    setStatus("running");

    startAnalysis(ticker)
      .then(({ session_id }) => {
        sessionRef.current = session_id;
        const unsub = subscribeToStream(
          session_id,
          (e) => {
            setEvents((prev) => [...prev, e]);
            setActiveNode(e.node);
          },
          async () => {
            setActiveNode(null);
            const result = await getResult(session_id);
            if (result.data) setFinalData(result.data);
            setStatus("done");
          },
          (err) => { setError(err); setStatus("error"); }
        );
        unsubRef.current = unsub;
      })
      .catch((err) => { setError(String(err)); setStatus("error"); });

    return () => { unsubRef.current?.(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  const fd      = finalData?.final_decision ?? {};
  const debate  = finalData?.debate_result  ?? {};
  const research = {
    fundamental: finalData?.fundamental_analysis ?? {},
    technical:   finalData?.technical_analysis   ?? {},
    sentiment:   finalData?.sentiment_analysis   ?? {},
    synthesized: finalData?.synthesized_research ?? {},
  };
  const risk = finalData?.risk_analysis ?? {};

  const completedCount = events.length;
  const totalNodes     = 8;

  return (
    <div className="flex-1 flex flex-col items-center px-4 py-8 gap-6 max-w-3xl mx-auto w-full">

      {/* Breadcrumb + header */}
      <div className="w-full space-y-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground/50">
          <Link href="/" className="hover:text-muted-foreground transition-colors">Analyze</Link>
          <span>/</span>
          <span className="font-mono text-muted-foreground/70">{ticker}</span>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-black font-mono tracking-tight">{ticker}</h2>
            <p className="text-xs text-muted-foreground/50 mt-0.5">
              {status === "running" ? "Multi-agent analysis in progress…" :
               status === "done"    ? "Analysis complete — review results below" :
               status === "error"   ? "Error during analysis" : ""}
            </p>
          </div>

          {status === "running" && (
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-xs font-mono text-muted-foreground/60">{completedCount}/{totalNodes} agents</div>
                <div className="w-24 h-1 bg-muted/40 rounded-full mt-1 overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-500"
                    style={{ width: `${(completedCount / totalNodes) * 100}%` }}
                  />
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-blue-400">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                Running
              </div>
            </div>
          )}

          {status === "done" && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Complete
            </div>
          )}
        </div>
      </div>

      {/* Error state */}
      {status === "error" && (
        <div className="w-full rounded-lg border border-red-800/40 bg-red-950/20 p-4">
          <div className="label-xs text-red-500/70 mb-1.5">Analysis Failed</div>
          <p className="text-sm text-red-300/80">
            {error || "An unexpected error occurred. Ensure the API server is running on port 8000."}
          </p>
        </div>
      )}

      {/* Agent Pipeline */}
      {(status === "running" || status === "done") && (
        <div className="w-full rounded-xl border border-border/35 bg-card/25 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="label-xs">Agent Pipeline</span>
            {status === "done" && <span className="label-xs text-emerald-500/60">All agents complete</span>}
          </div>
          <AgentTimeline events={events} activeNode={activeNode} />
        </div>
      )}

      {/* Verdict Card */}
      {status === "done" && fd.action && (
        <div className="w-full">
          <VerdictCard
            action={fd.action}
            confidence={fd.confidence ?? 0}
            ticker={ticker}
            timeHorizon={fd.time_horizon}
            priceTarget={fd.price_target}
            explanation={fd.explanation}
            keyReasons={fd.key_reasons ?? []}
            keyRisks={fd.key_risks ?? []}
          />
        </div>
      )}

      {/* Detail tabs */}
      {status === "done" && (
        <div className="w-full rounded-xl border border-border/35 bg-card/20 overflow-hidden">
          <Tabs defaultValue="debate">
            <div className="px-4 pt-3 border-b border-border/30">
              <TabsList className="bg-transparent gap-0 h-auto p-0">
                {["debate", "research", "risk"].map((tab) => (
                  <TabsTrigger
                    key={tab}
                    value={tab}
                    className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground px-4 py-2 text-xs font-semibold capitalize tracking-wide text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {tab === "debate" ? "Bull vs Bear" : tab === "research" ? "Research" : "Risk"}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
            <div className="p-4">
              <TabsContent value="debate">
                <DebateView debateResult={debate} />
              </TabsContent>
              <TabsContent value="research">
                <ResearchTabs research={research} />
              </TabsContent>
              <TabsContent value="risk">
                <RiskMeter risk={risk} />
              </TabsContent>
            </div>
          </Tabs>
        </div>
      )}

    </div>
  );
}
