import { useEffect, useState } from "react";
import { api, downloadFile } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle, Button } from "../components/ui";

export function Reports() {
  const [intake, setIntake] = useState<any[]>([]);
  const [dupes, setDupes] = useState<any[]>([]);
  const [risk, setRisk] = useState<any[]>([]);
  useEffect(() => {
    api.get("/reports/intake-vs-enrolment").then((r) => setIntake(r.data));
    api.get("/reports/duplicates").then((r) => setDupes(r.data));
    api.get("/reports/risk").then((r) => setRisk(r.data));
  }, []);
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Reports</h2>
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => downloadFile("/reports/intake-vs-enrolment?format=csv", "intake_vs_enrolment.csv")}>
          Export Intake vs Enrolment (CSV)
        </Button>
      </div>
      <Card>
        <CardHeader><CardTitle>Intake vs Enrolment ({intake.length})</CardTitle></CardHeader>
        <CardContent>
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-100"><tr><th className="px-2 py-1 text-left">Institution</th><th className="px-2 py-1 text-left">Programme</th><th className="px-2 py-1 text-left">Branch</th><th className="px-2 py-1 text-left">Used/Sanctioned</th><th className="px-2 py-1 text-left">Breach</th></tr></thead>
              <tbody>
                {intake.slice(0, 50).map((r: any, i: number) => (
                  <tr key={i} className="border-t">
                    <td className="px-2 py-1">{r.institution}</td>
                    <td className="px-2 py-1">{r.programme}</td>
                    <td className="px-2 py-1">{r.branch}</td>
                    <td className="px-2 py-1">{r.used}/{r.sanctioned_intake}</td>
                    <td className="px-2 py-1">{r.breach ? "YES" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Cross-institution Duplicates ({dupes.length})</CardTitle></CardHeader>
        <CardContent>
          <ul className="text-sm space-y-1">
            {dupes.slice(0, 20).map((d: any, i: number) => (
              <li key={i}>{d.apaar_id} — {d.count} records across {d.institutions.join(", ")}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Institution Risk ({risk.length})</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead className="bg-slate-100"><tr><th className="px-2 py-1 text-left">Institution</th><th className="px-2 py-1 text-left">State</th><th className="px-2 py-1 text-left">Risk</th><th className="px-2 py-1 text-left">Compliance</th></tr></thead>
            <tbody>
              {risk.sort((a: any, b: any) => b.risk_score - a.risk_score).slice(0, 15).map((r: any, i: number) => (
                <tr key={i} className="border-t">
                  <td className="px-2 py-1">{r.name}</td>
                  <td className="px-2 py-1">{r.state}</td>
                  <td className="px-2 py-1">{r.risk_score}</td>
                  <td className="px-2 py-1">{r.compliance_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}