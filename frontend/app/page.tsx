"use client";
import { useState, useEffect, useRef, KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { searchTickers, TickerSuggestion } from "@/lib/api";

type MarketKey = "US" | "India" | "Europe" | "Japan";

const MARKETS: Record<MarketKey, { label: string; tickers: string[] }> = {
  US:     { label: "🇺🇸 US",     tickers: ["NVDA","AAPL","MSFT","GOOG","AMZN","META","TSLA","JPM","V","NFLX"] },
  India:  { label: "🇮🇳 India",  tickers: ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","WIPRO.NS","ICICIBANK.NS","BAJFINANCE.NS","HINDUNILVR.NS"] },
  Europe: { label: "🇪🇺 Europe", tickers: ["ASML.AS","SAP.DE","LVMH.PA","NESN.SW","SHEL.L","SIE.DE","NOVN.SW","MC.PA"] },
  Japan:  { label: "🇯🇵 Japan",  tickers: ["7203.T","6758.T","9984.T","7974.T","6861.T","8306.T","6501.T","9432.T"] },
};

const JAPAN_NAMES: Record<string, string> = {
  "7203.T": "Toyota", "6758.T": "Sony", "9984.T": "SoftBank",
  "7974.T": "Nintendo", "6861.T": "Keyence", "8306.T": "Mitsubishi UFJ",
  "6501.T": "Hitachi", "9432.T": "NTT",
};

export default function Home() {
  const router = useRouter();
  const [market, setMarket] = useState<MarketKey>("US");
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<TickerSuggestion[]>([]);
  const [showDrop, setShowDrop] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  function navigate(ticker: string) {
    const clean = ticker.trim().toUpperCase();
    if (!clean) return;
    router.push(`/analyze/${clean}`);
  }

  function onInputChange(val: string) {
    setQuery(val);
    setActiveIdx(-1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (val.trim().length < 1) { setSuggestions([]); setShowDrop(false); return; }
    debounceRef.current = setTimeout(async () => {
      const results = await searchTickers(val.trim());
      setSuggestions(results);
      setShowDrop(results.length > 0);
    }, 300);
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActiveIdx((i) => Math.max(i - 1, -1)); }
    else if (e.key === "Enter") {
      if (activeIdx >= 0 && suggestions[activeIdx]) navigate(suggestions[activeIdx].symbol);
      else navigate(query);
      setShowDrop(false);
    }
    else if (e.key === "Escape") setShowDrop(false);
  }

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) setShowDrop(false);
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 gap-12 relative overflow-hidden">

      {/* Subtle grid + radial fade */}
      <div className="absolute inset-0 finance-grid pointer-events-none" />
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: "radial-gradient(ellipse 80% 50% at 50% 0%, oklch(0.18 0.02 248 / 0.45) 0%, transparent 70%)" }} />

      {/* Hero */}
      <div className="relative text-center space-y-3">
        <div className="inline-flex items-center gap-2 mb-3 px-3 py-1.5 rounded-full border border-border/40 bg-muted/20 backdrop-blur-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[11px] text-muted-foreground tracking-widest font-medium">LIVE ANALYSIS SYSTEM</span>
        </div>
        <h1 className="text-5xl font-black tracking-tight bg-gradient-to-b from-foreground to-foreground/60 bg-clip-text text-transparent">
          AI Investment Research
        </h1>
        <p className="text-muted-foreground text-sm max-w-md mx-auto leading-relaxed">
          Multi-agent analysis · Bull vs Bear debate · CVaR risk management
        </p>
      </div>

      {/* Search bar */}
      <div ref={wrapperRef} className="relative w-full max-w-xl z-10">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/40 text-sm select-none pointer-events-none">
              ⌕
            </span>
            <input
              autoFocus
              value={query}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyDown={onKey}
              onFocus={() => { if (suggestions.length > 0) setShowDrop(true); }}
              placeholder="Search stocks — NVDA, Reliance, ASML…"
              className="w-full bg-card/80 backdrop-blur-sm border border-border/70 rounded-lg pl-10 pr-4 py-3.5 text-sm font-mono placeholder:text-muted-foreground/35 focus:outline-none focus:ring-1 focus:ring-ring focus:border-border hover:border-border/90 transition-colors"
            />
          </div>
          <button
            onClick={() => { navigate(query); setShowDrop(false); }}
            className="px-6 py-3.5 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:opacity-90 active:scale-[0.98] transition-all whitespace-nowrap tracking-wide"
          >
            Analyze
          </button>
        </div>

        {/* Autocomplete dropdown */}
        {showDrop && (
          <div className="absolute top-full left-0 right-0 mt-1.5 z-50 rounded-lg border border-border/60 bg-card/95 backdrop-blur-md shadow-2xl overflow-hidden">
            <div className="px-3 py-1.5 border-b border-border/30">
              <span className="label-xs">Matching instruments</span>
            </div>
            {suggestions.map((s, i) => (
              <button
                key={s.symbol}
                onMouseDown={() => { navigate(s.symbol); setShowDrop(false); setQuery(""); }}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition-colors ${
                  i === activeIdx ? "bg-muted/70" : "hover:bg-muted/40"
                }`}
              >
                <span className="font-mono font-bold text-foreground w-32 shrink-0 truncate">{s.symbol}</span>
                <span className="text-muted-foreground truncate flex-1 text-xs">{s.name}</span>
                <span className="text-[10px] text-muted-foreground/45 shrink-0 font-mono uppercase">{s.exchange}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Market tabs + stocks */}
      <div className="relative w-full max-w-xl space-y-4">
        {/* Market tabs */}
        <div className="flex gap-1">
          {(Object.keys(MARKETS) as MarketKey[]).map((m) => (
            <button
              key={m}
              onClick={() => setMarket(m)}
              className={`flex-1 py-2 rounded-md text-xs font-semibold tracking-wide transition-all ${
                market === m
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/40 border border-border/40"
              }`}
            >
              {MARKETS[m].label}
            </button>
          ))}
        </div>

        {/* Separator */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-border/30" />
          <span className="label-xs">Popular</span>
          <div className="flex-1 h-px bg-border/30" />
        </div>

        {/* Stock chips */}
        <div className="flex flex-wrap gap-2">
          {MARKETS[market].tickers.map((t) => (
            <button
              key={t}
              onClick={() => navigate(t)}
              className="group px-3.5 py-2 text-xs font-mono border border-border/40 rounded-md text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/30 active:scale-95 transition-all"
            >
              {market === "Japan" ? (
                <span>
                  <span className="text-foreground/80 group-hover:text-foreground">{JAPAN_NAMES[t] ?? t}</span>
                  <span className="opacity-40 ml-1 text-[10px]">({t})</span>
                </span>
              ) : t}
            </button>
          ))}
        </div>
      </div>

    </div>
  );
}
