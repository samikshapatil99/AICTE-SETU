import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Badge } from "../components/ui";

export function Upload() {
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [instId, setInstId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/institutions").then((r) => {
      setInstitutions(r.data);
      if (r.data.length) setInstId(r.data[0].id);
    });
  }, []);

  const submit = async (e: any) => {
    e.preventDefault();
    if (!file || !instId) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const form = new FormData();
      form.append("institution_id", instId);
      form.append("file", file);
      const r = await api.post("/upload/csv", form);
      setResult(r.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };

  const confirm = async () => {
    if (!result) return;
    setLoading(true);
    try {
      const r = await api.post(`/upload/batch/${result.batchId}/confirm`, {});
      setResult({ ...result, confirmed: r.data });
    } catch (e: any) { setError(e.response?.data?.detail || e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Upload Student Records</h2>
      <Card>
        <CardHeader><CardTitle>Institution Upload (CSV)</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label>Institution</Label>
              <Select value={instId} onChange={(e: any) => setInstId(e.target.value)}>
                {institutions.map((i: any) => <option key={i.id} value={i.id}>{i.name} ({i.id})</option>)}
              </Select>
            </div>
            <div>
              <Label>CSV File</Label>
              <Input type="file" accept=".csv" onChange={(e: any) => setFile(e.target.files?.[0] || null)} />
            </div>
            <Button type="submit" disabled={loading || !file}>{loading ? "Validating..." : "Upload & Validate"}</Button>
          </form>
        </CardContent>
      </Card>
      {error && <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-md">{error}</div>}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Validation Result — {result.fileName}</CardTitle>
            <p className="text-sm text-slate-500">Batch: {result.batchId}</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: "Total", value: result.total },
                { label: "Valid", value: result.valid, color: "text-green-600" },
                { label: "Rejected", value: result.rejected, color: "text-red-600" },
                { label: "Warnings", value: result.warnings, color: "text-amber-600" },
              ].map((s) => (
                <div key={s.label} className="bg-slate-50 rounded-md p-3 text-center">
                  <div className="text-xs text-slate-500">{s.label}</div>
                  <div className={`text-xl font-bold ${s.color || "text-slate-800"}`}>{s.value}</div>
                </div>
              ))}
            </div>
            {result.intakeBreaches?.length > 0 && (
              <div className="bg-red-50 border border-red-200 p-4 rounded-md">
                <h4 className="font-semibold text-red-700 mb-2">Intake Breaches</h4>
                {result.intakeBreaches.map((b: any, i: number) => (
                  <div key={i} className="text-sm text-red-700">
                    {b.programme}/{b.branch}/{b.year}: {b.found === false ? "No approved intake" : `${b.normal_used}/${b.sanctioned} (supernumerary ${b.super_used}/${b.supernumerary_cap})`}
                  </div>
                ))}
              </div>
            )}
            {result.anomalies?.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 p-4 rounded-md">
                <h4 className="font-semibold text-amber-700 mb-2">Anomalies Detected</h4>
                {result.anomalies.map((a: any, i: number) => (
                  <div key={i} className="text-sm text-amber-700">[{a.severity}] {a.type}: {a.detail}</div>
                ))}
              </div>
            )}
            {result.errors?.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Errors ({result.errors.length})</h4>
                <div className="max-h-64 overflow-x-auto rounded-xl border">
                  <table className="w-full text-xs min-w-[640px]">
                    <thead className="bg-slate-100">
                      <tr><th className="px-2 py-1 text-left">Row</th><th className="px-2 py-1 text-left">APAAR</th><th className="px-2 py-1 text-left">Name</th><th className="px-2 py-1 text-left">Code</th><th className="px-2 py-1 text-left">Sev</th><th className="px-2 py-1 text-left">Message</th></tr>
                    </thead>
                    <tbody>
                      {result.errors.map((e: any, i: number) => (
                        <tr key={i} className="border-t">
                          <td className="px-2 py-1">{e.rowIndex}</td>
                          <td className="px-2 py-1">{e.apaar_id}</td>
                          <td className="px-2 py-1">{e.name}</td>
                          <td className="px-2 py-1">{e.code}</td>
                          <td className="px-2 py-1"><Badge variant={e.severity === "high" ? "destructive" : e.severity === "medium" ? "warning" : "info"}>{e.severity}</Badge></td>
                          <td className="px-2 py-1">{e.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {result.errors?.length > 0 && (
              <Button variant="outline" onClick={() => {
                const header = "rowIndex,apaar_id,name,code,severity,message,field";
                const rows = result.errors.map((e: any) => [e.rowIndex, e.apaar_id, e.name, e.code, e.severity, `"${String(e.message).replace(/"/g, '""')}"`, e.field].join(","));
                const csv = [header, ...rows].join("\\n");
                const blob = new Blob([csv], { type: "text/csv" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url; a.download = "validation_errors.csv";
                a.click(); URL.revokeObjectURL(url);
              }}>Download Error File (CSV)</Button>
            )}
            {!result.confirmed && (
              <Button onClick={confirm} disabled={loading}>{loading ? "Confirming..." : "Confirm & Push to Central Repository"}</Button>
            )}
            {result.confirmed && (
              <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-md text-sm">
                Confirmed: inserted {result.confirmed.inserted}, skipped {result.confirmed.skipped}.
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}