"use client";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Research = Record<string, any>;

function DataRow({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined || value === "") return null;
  const display = Array.isArray(value)
    ? value.join(", ")
    : typeof value === "object"
    ? JSON.stringify(value)
    : String(value);
  return (
    <div className="flex gap-3 py-2 border-b border-border/20 last:border-0 text-xs">
      <span className="text-muted-foreground/55 w-32 shrink-0 leading-relaxed">{label}</span>
      <span className="text-foreground/75 break-words flex-1 leading-relaxed">{display}</span>
    </div>
  );
}

function SignalChip({ value, className }: { value: string; className?: string }) {
  const v = value?.toLowerCase() ?? "";
  const color =
    v.includes("buy") || v.includes("bull") || v.includes("strong") || v.includes("undervalued") || v.includes("positive")
      ? "border-emerald-700/50 bg-emerald-950/30 text-emerald-300"
      : v.includes("sell") || v.includes("bear") || v.includes("overvalued") || v.includes("negative") || v.includes("weak")
      ? "border-red-700/50 bg-red-950/30 text-red-300"
      : "border-amber-700/50 bg-amber-950/30 text-amber-300";
  return (
    <span className={`inline-flex px-2.5 py-1 text-[10px] font-semibold tracking-wide rounded-md border ${color} ${className ?? ""}`}>
      {value}
    </span>
  );
}

function MetricBox({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border p-3 text-center ${highlight ? "border-border/50 bg-muted/10" : "border-border/25 bg-card/30"}`}>
      <div className="label-xs mb-1">{label}</div>
      <div className="text-sm font-mono font-semibold text-foreground/85">{value}</div>
    </div>
  );
}

export function ResearchTabs({ research }: {
  research: { fundamental: Research; technical: Research; sentiment: Research; synthesized: Research }
}) {
  const { fundamental: f, technical: t, sentiment: s, synthesized: syn } = research;

  return (
    <Tabs defaultValue="fundamental">
      <TabsList className="w-full bg-muted/20 border border-border/30">
        <TabsTrigger value="fundamental" className="flex-1 text-xs">Fundamental</TabsTrigger>
        <TabsTrigger value="technical"   className="flex-1 text-xs">Technical</TabsTrigger>
        <TabsTrigger value="sentiment"   className="flex-1 text-xs">Sentiment</TabsTrigger>
        <TabsTrigger value="synthesis"   className="flex-1 text-xs">Synthesis</TabsTrigger>
      </TabsList>

      {/* Fundamental */}
      <TabsContent value="fundamental" className="mt-3 space-y-3">
        <div className="flex gap-2 flex-wrap">
          {f.valuation_signal && <SignalChip value={f.valuation_signal} />}
          {f.financial_health  && <SignalChip value={f.financial_health} />}
          {f.growth_outlook    && <SignalChip value={f.growth_outlook} />}
        </div>
        {f.confidence && (
          <div className="grid grid-cols-3 gap-2">
            <MetricBox label="Confidence" value={`${Math.round(f.confidence * 100)}%`} highlight />
          </div>
        )}
        <div className="border border-border/25 rounded-lg divide-y divide-border/20">
          <DataRow label="Key Strengths" value={f.key_strengths} />
          <DataRow label="Key Risks"     value={f.key_risks} />
          <DataRow label="Summary"       value={f.summary} />
        </div>
      </TabsContent>

      {/* Technical */}
      <TabsContent value="technical" className="mt-3 space-y-3">
        <div className="flex gap-2 flex-wrap">
          {t.trend    && <SignalChip value={t.trend} />}
          {t.momentum && <SignalChip value={t.momentum} />}
        </div>
        {(t.current_price || t.rsi || t.ema) && (
          <div className="grid grid-cols-3 gap-2">
            {t.current_price && <MetricBox label="Price"   value={String(t.current_price)} highlight />}
            {t.rsi           && <MetricBox label="RSI"     value={`${t.rsi.value?.toFixed(1)} · ${t.rsi.signal}`} />}
            {t.ema           && <MetricBox label="EMA 20/50" value={`${t.ema.ema20?.toFixed(0)} / ${t.ema.ema50?.toFixed(0)}`} />}
          </div>
        )}
        <div className="border border-border/25 rounded-lg divide-y divide-border/20">
          <DataRow label="MACD Crossover"  value={t.macd?.crossover} />
          <DataRow label="Key Signals"     value={t.key_signals} />
          <DataRow label="Support"         value={t.support_level} />
          <DataRow label="Resistance"      value={t.resistance_level} />
          <DataRow label="Summary"         value={t.summary} />
        </div>
      </TabsContent>

      {/* Sentiment */}
      <TabsContent value="sentiment" className="mt-3 space-y-3">
        <div className="flex gap-2 flex-wrap">
          {s.overall_sentiment && <SignalChip value={s.overall_sentiment} />}
          {s.sentiment_score !== undefined && (
            <span className="inline-flex px-2.5 py-1 text-[10px] font-semibold tracking-wide rounded-md border border-border/40 bg-muted/20 text-muted-foreground font-mono">
              Score: {Number(s.sentiment_score).toFixed(2)}
            </span>
          )}
        </div>
        <div className="border border-border/25 rounded-lg divide-y divide-border/20">
          <DataRow label="News Sentiment"   value={s.news_sentiment} />
          <DataRow label="Social Sentiment" value={s.social_sentiment} />
          <DataRow label="Key Themes"       value={s.key_themes} />
          <DataRow label="Catalysts"        value={s.catalyst_events} />
          <DataRow label="Summary"          value={s.summary} />
        </div>
      </TabsContent>

      {/* Synthesis */}
      <TabsContent value="synthesis" className="mt-3 space-y-3">
        <div className="flex gap-2 flex-wrap">
          {syn.overall_signal   && <SignalChip value={syn.overall_signal} />}
          {syn.signal_alignment && (
            <span className="inline-flex px-2.5 py-1 text-[10px] font-semibold tracking-wide rounded-md border border-border/40 bg-muted/20 text-muted-foreground">
              {syn.signal_alignment}
            </span>
          )}
          {syn.data_quality && (
            <span className="inline-flex px-2.5 py-1 text-[10px] font-semibold tracking-wide rounded-md border border-border/40 bg-muted/20 text-muted-foreground">
              data: {syn.data_quality}
            </span>
          )}
        </div>
        <div className="border border-border/25 rounded-lg divide-y divide-border/20">
          <DataRow label="Bull Arguments"     value={syn.bull_arguments} />
          <DataRow label="Bear Arguments"     value={syn.bear_arguments} />
          <DataRow label="Key Uncertainties"  value={syn.key_uncertainties} />
          <DataRow label="Investment Context" value={syn.investment_context} />
        </div>
      </TabsContent>
    </Tabs>
  );
}
