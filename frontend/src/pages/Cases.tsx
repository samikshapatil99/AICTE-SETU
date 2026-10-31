import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Select } from "../components/ui";

export function Cases() {
  const [cases, setCases] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);
  const [flags, setFlags] = useState<any[]>([]);

  const load = () => {
    api.get("/compliance/cases").then((r) => setCases(r.data)).catch(() => {});
    api.get("/dashboard/aicte/flags?status=open").then((r) => setFlags(r.data)).catch(() => {});
  };
  useEffect(load, []);

  const openCase = async (flagId: number) => {
    const r = await api.post(`/compliance/cases/from-flag/${flagId}`, {});
    load();
    await openDetail(r.data.case_id);
  };

  const openDetail = async (id: string) => {
    setSelected(id);
    const r = await api.get(`/compliance/cases/${id}`);
    setDetail(r.data);
  };

  const setStatus = async (status: string) => {
    if (!selected) return;
    await api.post(`/compliance/cases/${selected}/status`, { status, rationale: "status change" });
    await openDetail(selected);
    load();
  };

  const resolve = async (outcome: string) => {
    if (!selected) return;
    const rationale = prompt("Reviewer rationale (required):") || "";
    if (!rationale) return;
    await api.post(`/compliance/cases/${selected}/resolve`, { outcome, rationale });
    await openDetail(selected);
    load();
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Compliance Cases (Explainable)</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle>Open Flags → Cases</CardTitle></CardHeader>
          <CardContent>
            <ul className="divide-y max-h-[500px] overflow-auto">
              {flags.map((f: any) => (
                <li key={f.id} className="py-2">
                  <div className="text-xs font-medium">{f.flag_type} · {f.severity}</div>
                  <div className="text-xs text-slate-500">{f.institution_id} · {f.reason}</div>
                  <Button size="sm" className="mt-1" onClick={() => openCase(f.id)}>Convert to Case</Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Cases</CardTitle></CardHeader>
          <CardContent>
            <ul className="divide-y max-h-[500px] overflow-auto">
              {cases.map((c: any) => (
                <li key={c.id} onClick={() => openDetail(c.id)} className={`py-2 cursor-pointer ${selected === c.id ? "bg-navy-50" : ""}`}>
                  <div className="text-xs font-medium">{c.title}</div>
                  <div className="text-xs text-slate-500">{c.status} · {c.institution_id}</div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card className="md:col-span-1">
          <CardHeader><CardTitle>Case Detail</CardTitle></CardHeader>
          <CardContent>
            {!detail && <p className="text-slate-500 text-sm">Select a case.</p>}
            {detail && (
              <div className="space-y-3 text-sm">
                <div><b>Status:</b> {detail.case.status}</div>
                <div className="flex gap-2 flex-wrap">
                  {["evidence_requested", "under_review"].map((s) => (
                    <Button key={s} size="sm" variant="outline" onClick={() => setStatus(s)}>{s}</Button>
                  ))}
                  <Button size="sm" variant="destructive" onClick={() => resolve("escalated")}>Escalate</Button>
                  <Button size="sm" variant="secondary" onClick={() => resolve("resolved")}>Resolve</Button>
                </div>
                {["observed_fact", "rule_evidence", "system_inference", "impact", "recommended_action"].map((kind) => (
                  <div key={kind} className="border rounded-md p-2">
                    <div className="font-semibold text-xs uppercase text-slate-600">{kind.replace("_", " ")}</div>
                    {(detail.panels[kind] || []).map((p: any, i: number) => (
                      <pre key={i} className="text-xs bg-slate-50 p-2 rounded mt-1 whitespace-pre-wrap">{p.content}</pre>
                    ))}
                  </div>
                ))}
                <div>
                  <div className="font-semibold text-xs uppercase text-slate-600">Decision Record</div>
                  {detail.decisions.length === 0 && <p className="text-xs text-slate-500">No decisions yet.</p>}
                  {detail.decisions.map((d: any, i: number) => (
                    <div key={i} className="text-xs border-t pt-1 mt-1">
                      <div>{d.reviewer} ({d.reviewer_role}) → {d.outcome}</div>
                      <div className="text-slate-500">{d.rationale}</div>
                      <div className="text-slate-400">{d.decided_at}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}