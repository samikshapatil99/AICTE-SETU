import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle, Button, Select } from "../components/ui";

export function Replay() {
  const [batches, setBatches] = useState<any[]>([]);
  const [batchId, setBatchId] = useState("");
  const [ruleSets, setRuleSets] = useState<any[]>([]);
  const [rsA, setRsA] = useState("RULESET-A-2025");
  const [rsB, setRsB] = useState("RULESET-B-2025");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/dashboard/batches").then((r) => { setBatches(r.data); if (r.data.length) setBatchId(r.data[0].id); }).catch(() => {});
    api.get("/compliance/rule-sets").then((r) => setRuleSets(r.data)).catch(() => {});
  }, []);

  const run = async () => {
    if (!batchId) return;
    setLoading(true);
    try {
      const r = await api.post(`/compliance/batches/${batchId}/replay`, { rule_set_a: rsA, rule_set_b: rsB });
      setResult(r.data);
    } catch (e: any) { alert(e.response?.data?.detail || e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Rule Replay (A vs B)</h2>
      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium">Batch</label>
              <Select value={batchId} onChange={(e: any) => setBatchId(e.target.value)}>
                {batches.map((b: any) => <option key={b.id} value={b.id}>{b.id.slice(0,8)} · {b.status}</option>)}
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Rule Set A</label>
              <Select value={rsA} onChange={(e: any) => setRsA(e.target.value)}>
                {ruleSets.map((r: any) => <option key={r.id} value={r.id}>{r.name} ({r.version})</option>)}
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Rule Set B</label>
              <Select value={rsB} onChange={(e: any) => setRsB(e.target.value)}>
                {ruleSets.map((r: any) => <option key={r.id} value={r.id}>{r.name} ({r.version})</option>)}
              </Select>
            </div>
          </div>
          <Button onClick={run} disabled={loading}>{loading ? "Replaying..." : "Replay under both versions"}</Button>
        </CardContent>
      </Card>
      {result && (
        <Card>
          <CardHeader><CardTitle>Diff</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm text-slate-600 mb-3">{result.explanation}</p>
            <div className="max-h-[500px] overflow-auto">
              <table className="w-full text-xs">
                <thead className="bg-slate-100">
                  <tr><th className="px-2 py-1">Row</th><th className="px-2 py-1">Outcome A</th><th className="px-2 py-1">Outcome B</th><th className="px-2 py-1">Changed?</th><th className="px-2 py-1">Rules A</th><th className="px-2 py-1">Rules B</th></tr>
                </thead>
                <tbody>
                  {result.diff.map((d: any, i: number) => (
                    <tr key={i} className="border-t">
                      <td className="px-2 py-1">{d.row}</td>
                      <td className="px-2 py-1">{d.a?.outcome}</td>
                      <td className="px-2 py-1">{d.b?.outcome}</td>
                      <td className="px-2 py-1">{d.changed ? "YES" : "no"}</td>
                      <td className="px-2 py-1">{d.a?.errors?.map((e: any) => e.code).join(", ")}</td>
                      <td className="px-2 py-1">{d.b?.errors?.map((e: any) => e.code).join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}