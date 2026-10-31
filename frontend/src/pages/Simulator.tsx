import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle, Button, Input, Label, Select } from "../components/ui";

export function Simulator() {
  const [students, setStudents] = useState<any[]>([]);
  const [sid, setSid] = useState("");
  const [ruleSets, setRuleSets] = useState<any[]>([]);
  const [rs, setRs] = useState("RULESET-A-2025");
  const [proposed, setProposed] = useState({ admission_date: "2025-08-15" });
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/students?limit=50").then((r) => { setStudents(r.data); if (r.data.length) setSid(r.data[0].id); }).catch(() => {});
    api.get("/compliance/rule-sets").then((r) => setRuleSets(r.data)).catch(() => {});
  }, []);

  const run = async () => {
    if (!sid) return;
    setLoading(true);
    try {
      const r = await api.post(`/compliance/students/${sid}/preview-correction`, { proposed, rule_set_id: rs });
      setResult(r.data);
    } catch (e: any) { alert(e.response?.data?.detail || e.message); }
    finally { setLoading(false); }
  };

  const apply = async () => {
    if (!sid) return;
    await api.post(`/compliance/students/${sid}/update`, { changes: proposed, reason: "correction" });
    alert("Applied (versioned). Original finding preserved.");
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Compliance Impact Simulator (Preview Correction)</h2>
      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label>Student</Label>
              <Select value={sid} onChange={(e: any) => setSid(e.target.value)}>
                {students.map((s: any) => <option key={s.id} value={s.id}>{s.name} ({s.apaar_id})</option>)}
              </Select>
            </div>
            <div>
              <Label>Rule Set</Label>
              <Select value={rs} onChange={(e: any) => setRs(e.target.value)}>
                {ruleSets.map((r: any) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </Select>
            </div>
            <div>
              <Label>Proposed admission_date</Label>
              <Input value={proposed.admission_date} onChange={(e: any) => setProposed({ ...proposed, admission_date: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={run} disabled={loading}>{loading ? "Simulating..." : "Preview (no commit)"}</Button>
            <Button variant="secondary" onClick={apply}>Apply Correction (versioned)</Button>
          </div>
        </CardContent>
      </Card>
      {result && (
        <Card>
          <CardHeader><CardTitle>Before / After</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="border rounded-md p-3">
                <div className="font-semibold mb-2">Before</div>
                <div className="text-sm">Outcome: <b>{result.before.outcome}</b></div>
                <pre className="text-xs bg-slate-50 p-2 rounded mt-2">{JSON.stringify(result.before.errors, null, 2)}</pre>
              </div>
              <div className="border rounded-md p-3">
                <div className="font-semibold mb-2">After (proposed)</div>
                <div className="text-sm">Outcome: <b>{result.after.outcome}</b></div>
                <pre className="text-xs bg-slate-50 p-2 rounded mt-2">{JSON.stringify(result.after.errors, null, 2)}</pre>
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-3">Original finding preserved: {String(result.original_preserved)}. Open cases before: {result.open_cases_before}.</p>
            <p className="text-xs text-slate-500">Affected intake summary (current): {JSON.stringify(result.intake_summary?.length)} programmes.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}