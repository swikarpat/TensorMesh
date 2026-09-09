"use client";

import { useState } from "react";
import axios from "axios";
import { Activity, AlertTriangle, Database, Layers3, Loader2, Network, ScanSearch, ShieldCheck, Waves } from "lucide-react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

type Hypothesis = {
  agent_id: string;
  conclusion: string;
  confidence_score: number;
  evidence: Record<string, unknown>;
};

type EvaluationReport = {
  deposit_id: string;
  borehole_id: string;
  impedance_statistics: {
    sample_count: number;
    min: number;
    max: number;
    mean: number;
    frequency_count: number;
    spectral_anomaly_flags: boolean[];
  };
  assay_grade_status: {
    evaluations: Array<{
      element: string;
      observed_max_ppm: number;
      threshold_ppm: number;
      anomaly_detected: boolean;
      sample_count: number;
    }>;
    anomalous_elements: string[];
  };
  stratigraphy: { intervals: Array<{ top_depth_m: number; base_depth_m: number; lithology: string }> };
  a2a_reasoning: {
    verdict: string;
    confidence_score: number;
    hypotheses: Hypothesis[];
    handoffs: Array<{ envelope: { message_id: string } }>;
  };
  supply_impact: Array<{
    mineral: string;
    bottleneck_entities: string[];
    smelter_concentration_risk: number;
    dependencies: Array<{ source: string; quantity: number }>;
  }>;
  checkpoint_keys: string[];
  commercial_viability_verdict: string;
};

const defaultTrace = "0.05, 0.10, -0.03, 0.02, 0.00, 0.08, -0.04, 0.03";
const agentLabels: Record<string, string> = {
  geochemist: "Geochemist",
  structural_geologist: "Structural Geologist",
  economic_assessor: "Economic Assessor",
};

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export default function CommandCenter() {
  const [depositId, setDepositId] = useState("DEP-ALPHA-01");
  const [boreholeId, setBoreholeId] = useState("BH-ALPHA-07");
  const [depthRange, setDepthRange] = useState("0, 120");
  const [trace, setTrace] = useState(defaultTrace);
  const [assays, setAssays] = useState({ Li: "1400", Co: "450", Nd: "700" });
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [error, setError] = useState("");

  const supplyNodes: Node[] = report
    ? [
        {
          id: "deposit",
          position: { x: 520, y: 180 },
          data: { label: report.deposit_id },
          style: { background: "#0f766e", color: "#ecfeff", border: "1px solid #2dd4bf", borderRadius: 4, padding: 12, fontWeight: 700 },
        },
        ...report.supply_impact.flatMap((impact, index) =>
          impact.bottleneck_entities.map((entity, entityIndex) => ({
            id: `smelter-${index}-${entityIndex}`,
            position: { x: 80 + index * 180, y: 420 },
            data: { label: `${entity}\n${impact.mineral} · ${percent(impact.smelter_concentration_risk)}` },
            style: { background: impact.smelter_concentration_risk > 0.7 ? "#7f1d1d" : "#164e63", color: "#f8fafc", border: "1px solid #fb7185", borderRadius: 4, padding: 10, whiteSpace: "pre-line" },
          })),
        ),
      ]
    : [];
  const supplyEdges: Edge[] = report
    ? report.supply_impact.flatMap((impact, index) =>
        impact.bottleneck_entities.map((_, entityIndex) => ({
          id: `supply-edge-${index}-${entityIndex}`,
          source: `smelter-${index}-${entityIndex}`,
          target: "deposit",
          animated: true,
          label: impact.mineral,
          style: { stroke: impact.smelter_concentration_risk > 0.7 ? "#fb7185" : "#38bdf8", strokeWidth: 2 },
        })),
      )
    : [];

  async function evaluateDeposit() {
    setIsEvaluating(true);
    setError("");
    try {
      const depths = depthRange.split(",").map((value) => Number(value.trim()));
      const rawTrace = trace.split(",").map((value) => Number(value.trim()));
      const response = await axios.post<EvaluationReport>("http://localhost:8000/api/deposits/evaluate", {
        deposit_id: depositId,
        borehole_id: boreholeId,
        raw_seismic_trace: rawTrace,
        elemental_assays: Object.fromEntries(Object.entries(assays).map(([key, value]) => [key, Number(value)])),
        depth_range: depths,
      });
      setReport(response.data);
    } catch (requestError) {
      setError(axios.isAxiosError(requestError) ? requestError.response?.data?.detail ?? requestError.message : "Evaluation failed");
    } finally {
      setIsEvaluating(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#071116] text-slate-200">
      <header className="border-b border-cyan-950/70 bg-[#0a1920] px-6 py-5 lg:px-10">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center border border-cyan-400/50 bg-cyan-400/10 text-cyan-300"><Activity size={21} /></div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-400">TensorMesh / Field Intelligence</p>
              <h1 className="text-2xl font-semibold tracking-tight text-white">Subsurface Command Center</h1>
            </div>
          </div>
          <div className="flex items-center gap-2 border border-emerald-800/70 bg-emerald-950/30 px-3 py-2 text-xs text-emerald-300"><ShieldCheck size={14} /> Native compute online</div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1500px] gap-5 p-5 lg:grid-cols-[310px_1fr] lg:p-8">
        <aside className="h-fit border border-slate-800 bg-[#0b1b22] p-5">
          <div className="mb-6 flex items-center gap-2 text-sm font-semibold text-white"><ScanSearch size={17} className="text-cyan-300" /> Evaluation input</div>
          <div className="space-y-4">
            <label className="block text-xs uppercase tracking-wider text-slate-500">Deposit ID<input value={depositId} onChange={(event) => setDepositId(event.target.value)} className="mt-1 w-full border border-slate-700 bg-[#071116] px-3 py-2 text-sm text-white outline-none focus:border-cyan-400" /></label>
            <label className="block text-xs uppercase tracking-wider text-slate-500">Borehole ID<input value={boreholeId} onChange={(event) => setBoreholeId(event.target.value)} className="mt-1 w-full border border-slate-700 bg-[#071116] px-3 py-2 text-sm text-white outline-none focus:border-cyan-400" /></label>
            <label className="block text-xs uppercase tracking-wider text-slate-500">Depth range (m)<input value={depthRange} onChange={(event) => setDepthRange(event.target.value)} className="mt-1 w-full border border-slate-700 bg-[#071116] px-3 py-2 text-sm text-white outline-none focus:border-cyan-400" /></label>
            <label className="block text-xs uppercase tracking-wider text-slate-500">Seismic trace<input value={trace} onChange={(event) => setTrace(event.target.value)} className="mt-1 w-full border border-slate-700 bg-[#071116] px-3 py-2 text-sm text-white outline-none focus:border-cyan-400" /></label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(assays).map(([element, value]) => <label key={element} className="text-xs uppercase tracking-wider text-slate-500">{element}<input value={value} onChange={(event) => setAssays({ ...assays, [element]: event.target.value })} className="mt-1 w-full border border-slate-700 bg-[#071116] px-2 py-2 text-sm text-white outline-none focus:border-cyan-400" /></label>)}
            </div>
            <button onClick={evaluateDeposit} disabled={isEvaluating} className="flex w-full items-center justify-center gap-2 bg-cyan-400 px-4 py-3 text-sm font-bold text-[#071116] transition hover:bg-cyan-300 disabled:opacity-50">{isEvaluating ? <Loader2 size={16} className="animate-spin" /> : <Waves size={16} />} Evaluate deposit</button>
            {error && <p className="border border-rose-900 bg-rose-950/40 p-3 text-xs text-rose-300">{error}</p>}
          </div>
        </aside>

        <section className="min-w-0 space-y-5">
          {!report && <div className="flex min-h-[420px] items-center justify-center border border-dashed border-slate-800 bg-[#09171d] text-center"><div><Layers3 size={34} className="mx-auto mb-3 text-cyan-400" /><p className="text-lg font-medium text-white">Awaiting subsurface evaluation</p><p className="mt-1 text-sm text-slate-500">Submit a seismic trace to activate the mesh.</p></div></div>}
          {report && <>
            <div className="grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
              <section className="border border-slate-800 bg-[#0b1b22] p-5"><div className="mb-5 flex items-center justify-between"><div><p className="text-[11px] uppercase tracking-[0.22em] text-cyan-400">01 / Seismic inversion</p><h2 className="mt-1 text-lg font-semibold text-white">Impedance layers & spectral scan</h2></div><Database size={19} className="text-cyan-400" /></div><div className="grid grid-cols-3 gap-3">{[["Samples", report.impedance_statistics.sample_count], ["Mean Z", Math.round(report.impedance_statistics.mean)], ["Bands", report.impedance_statistics.frequency_count]].map(([label, value]) => <div key={label} className="border border-slate-800 bg-[#071116] p-3"><p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-1 text-xl font-semibold text-white">{value}</p></div>)}</div><div className="mt-5 flex h-24 items-end gap-1 border-b border-slate-700 px-2">{report.impedance_statistics.spectral_anomaly_flags.map((flag, index) => <div key={index} className={`flex-1 ${flag ? "bg-rose-400" : "bg-cyan-400/60"}`} style={{ height: `${25 + ((index * 17) % 65)}%` }} title={`Band ${index + 1}: ${flag ? "anomaly" : "nominal"}`} />)}</div><p className="mt-2 text-xs text-slate-500">Spectral anomaly flags: <span className="text-rose-300">{report.impedance_statistics.spectral_anomaly_flags.filter(Boolean).length}</span> / {report.impedance_statistics.frequency_count}</p></section>
              <section className="border border-slate-800 bg-[#0b1b22] p-5"><div className="mb-5 flex items-center gap-2"><AlertTriangle size={18} className="text-amber-300" /><div><p className="text-[11px] uppercase tracking-[0.22em] text-amber-300">02 / Geochemistry</p><h2 className="mt-1 text-lg font-semibold text-white">Assay & stratigraphy feed</h2></div></div><div className="space-y-3">{report.assay_grade_status.evaluations.map((evaluation) => <div key={evaluation.element} className="border-b border-slate-800 pb-2"><div className="flex justify-between text-sm"><span className="font-medium text-white">{evaluation.element}</span><span className={evaluation.anomaly_detected ? "text-emerald-300" : "text-slate-400"}>{evaluation.observed_max_ppm} / {evaluation.threshold_ppm} ppm</span></div><div className="mt-2 h-1 bg-slate-800"><div className={evaluation.anomaly_detected ? "h-1 bg-emerald-400" : "h-1 bg-slate-500"} style={{ width: `${Math.min(100, (evaluation.observed_max_ppm / evaluation.threshold_ppm) * 100)}%` }} /></div></div>)}</div><p className="mt-4 text-xs text-slate-500">{report.stratigraphy.intervals.length} stratigraphic intervals inspected from {report.borehole_id}.</p></section>
            </div>

            <section className="border border-slate-800 bg-[#0b1b22] p-5"><div className="mb-5 flex items-center justify-between"><div><p className="text-[11px] uppercase tracking-[0.22em] text-violet-300">03 / A2A reasoning mesh</p><h2 className="mt-1 text-lg font-semibold text-white">Hypothesis timeline</h2></div><span className="border border-violet-800 bg-violet-950/30 px-3 py-1 text-xs text-violet-200">{percent(report.a2a_reasoning.confidence_score)} final confidence</span></div><div className="grid gap-3 lg:grid-cols-3">{report.a2a_reasoning.hypotheses.map((hypothesis) => <article key={hypothesis.agent_id} className="border border-slate-800 bg-[#071116] p-4"><div className="flex items-center justify-between"><h3 className="font-medium text-white">{agentLabels[hypothesis.agent_id] ?? hypothesis.agent_id}</h3><span className="text-xs text-violet-300">{percent(hypothesis.confidence_score)}</span></div><p className="mt-3 text-sm text-cyan-200">{hypothesis.conclusion.replaceAll("_", " ")}</p><p className="mt-3 break-all font-mono text-[10px] text-slate-500">Evidence: {JSON.stringify(hypothesis.evidence)}</p></article>)}</div><div className="mt-4 flex flex-wrap gap-2">{report.checkpoint_keys.map((key) => <span key={key} className="border border-slate-700 px-2 py-1 font-mono text-[10px] text-slate-400">{key}</span>)}</div></section>

            <section className="border border-slate-800 bg-[#0b1b22] p-5"><div className="mb-4 flex items-center gap-2"><Network size={18} className="text-sky-300" /><div><p className="text-[11px] uppercase tracking-[0.22em] text-sky-300">04 / Downstream impact</p><h2 className="mt-1 text-lg font-semibold text-white">Critical mineral supply dependencies</h2></div></div><div className="h-[330px] border border-slate-800 bg-[#071116]"><ReactFlow nodes={supplyNodes} edges={supplyEdges} fitView><Background color="#1e3a46" gap={18} /><Controls /><MiniMap nodeColor="#14b8a6" /></ReactFlow></div><div className="mt-4 flex items-center justify-between border-t border-slate-800 pt-4"><span className="text-sm text-slate-400">Commercial viability verdict</span><strong className="text-lg capitalize text-emerald-300">{report.commercial_viability_verdict.replaceAll("_", " ")}</strong></div></section>
          </>}
        </section>
      </div>
    </main>
  );
}
