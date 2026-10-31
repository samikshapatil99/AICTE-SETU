import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui";

export function Institutions() {
  const [list, setList] = useState<any[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);

  useEffect(() => { api.get("/institutions").then((r) => setList(r.data)); }, []);

  const open = async (id: string) => {
    setSelected(id);
    const r = await api.get(`/institutions/${id}`);
    const intake = await api.get(`/institutions/${id}/intake-summary`);
    setDetail({ ...r.data, intakeSummary: intake.data });
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Institutions</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <ul className="divide-y max-h-[600px] overflow-auto">
              {list.map((i: any) => (
                <li key={i.id} onClick={() => open(i.id)} className={`py-2 px-2 cursor-pointer rounded ${selected === i.id ? "bg-navy-50" : "hover:bg-slate-50"}`}>
                  <div className="font-medium text-sm">{i.name}</div>
                  <div className="text-xs text-slate-500">{i.state} · Risk {i.risk_score} · Compliance {i.compliance_score}</div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card className="md:col-span-2">
          <CardContent className="p-6">
            {!detail && <p className="text-slate-500">Select an institution.</p>}
            {detail && (
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold">{detail.name}</h3>
                  <p className="text-sm text-slate-500">{detail.state} · {detail.type} · Risk {detail.risk_score} · Compliance {detail.compliance_score} · Completeness {detail.data_completeness}%</p>
                </div>
                <h4 className="font-semibold">Approved Intake & Utilisation</h4>
                <table className="w-full text-sm">
                  <thead className="bg-slate-100">
                    <tr><th className="px-2 py-1 text-left">Programme</th><th className="px-2 py-1 text-left">Branch</th><th className="px-2 py-1 text-left">Year</th><th className="px-2 py-1 text-left">Sanctioned</th><th className="px-2 py-1 text-left">Used</th><th className="px-2 py-1 text-left">Supernum Cap/Used</th><th className="px-2 py-1 text-left">Util %</th></tr>
                  </thead>
                  <tbody>
                    {detail.intakeSummary?.map((it: any, i: number) => (
                      <tr key={i} className="border-t">
                        <td className="px-2 py-1">{it.programme}</td>
                        <td className="px-2 py-1">{it.branch}</td>
                        <td className="px-2 py-1">{it.year}</td>
                        <td className="px-2 py-1">{it.sanctioned_intake}</td>
                        <td className="px-2 py-1">{it.used}</td>
                        <td className="px-2 py-1">{it.supernumerary_cap}/{it.supernumerary_used}</td>
                        <td className={`px-2 py-1 ${it.utilisation > 100 ? "text-red-600 font-bold" : ""}`}>{it.utilisation}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}