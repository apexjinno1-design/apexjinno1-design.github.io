"use client";
import { useEffect, useRef, useState } from "react";
import { CandlestickSeries, ColorType, HistogramSeries, LineSeries, LineStyle, createChart } from "lightweight-charts";
import type { Bar, Plan } from "@/lib/types";

export default function PriceChart({ bars, plan, pivot, baseLow }: { bars: Bar[]; plan?: Plan; pivot?: number; baseLow?: number }) {
  const element = useRef<HTMLDivElement>(null);
  const [range, setRange] = useState(126);
  useEffect(() => {
    if (!element.current || !bars.length) return;
    const chart = createChart(element.current, { height: 480,
      layout: { background: { type: ColorType.Solid, color: "#ffffff" }, textColor: "#77858b", attributionLogo: true },
      grid: { vertLines: { color: "#f2f4f5" }, horzLines: { color: "#f2f4f5" } },
      rightPriceScale: { borderColor: "#e9eeed" }, timeScale: { borderColor: "#e9eeed" },
      crosshair: { mode: 0 },
    });
    const candles = chart.addSeries(CandlestickSeries, { upColor: "#16896b", downColor: "#dd726a", borderVisible: false, wickUpColor: "#16896b", wickDownColor: "#dd726a" });
    candles.setData(bars.map(b => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close })));
    const moving = [["sma10", "#d6a44b"], ["sma20", "#627dc4"], ["sma50", "#bb83ad"]] as const;
    moving.forEach(([key, color]) => { const line = chart.addSeries(LineSeries, { color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false }); line.setData(bars.filter(b => b[key] != null).map(b => ({ time: b.time, value: b[key]! }))); });
    const levels: [number | undefined, string, string][] = [[pivot, "#5273ac", "Base high / pivot"], [plan?.entry, "#16896b", "Planning entry"], [plan?.stop, "#d56a63", "Technical stop"], [plan?.target, "#99ac77", "Hypothetical target"]];
    if (baseLow != null) levels.push([baseLow, "#9ba9b3", "Base low"]);
    levels.forEach(([price, color, title]) => { if (price != null) candles.createPriceLine({ price, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title }); });
    const vol = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false }, 1);
    vol.setData(bars.map(b => ({ time: b.time, value: b.volume, color: b.close >= b.open ? "#c6e4d8" : "#efd4d0" })));
    chart.panes()[0].setHeight(370); chart.panes()[1].setHeight(90);
    const shown = bars.slice(-range);
    chart.timeScale().setVisibleRange({ from: shown[0].time, to: shown[shown.length - 1].time });
    const observer = new ResizeObserver(entries => chart.applyOptions({ width: entries[0].contentRect.width }));
    observer.observe(element.current);
    return () => { observer.disconnect(); chart.remove(); };
  }, [bars, plan, pivot, range, baseLow]);
  return <section className="chart-panel"><div className="chart-toolbar"><div><span className="legend-key sma10"/>SMA 10 <span className="legend-key sma20"/>SMA 20 <span className="legend-key sma50"/>SMA 50</div><div>{[[63, "3M"], [126, "6M"], [260, "1Y"]].map(([n, label]) => <button key={n} onClick={() => setRange(Number(n))} className={range === n ? "selected" : ""}>{label}</button>)}</div></div><div ref={element} role="img" aria-label="Interactive daily candlestick and volume chart with moving averages and trade levels"/>
      <div className="chart-caption">Daily · adjusted OHLCV · Dashed lines mark the selected base and conditional plan. Drag to pan; scroll to zoom.</div></section>;
}
