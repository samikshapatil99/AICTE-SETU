import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from "../components/ui";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

export function Dashboard() {
  const [overview, setOverview] = useState<any>(null);
  const [flagged, setFlagged] = useState<any[]>([]);
  const [util, setUtil] = useState<any[]>([]);
  const [flags, setFlags] = useState<any[]>([]);

  const load = () => {
    api.get("/dashboard/aicte/overview").then((r) => setOverview(r.data));
    api.get("/dashboard/aicte/flagged").then((r) => setFlagged(r.data));
    api.get("/dashboard/aicte/intake-utilisation").then((r) => setUtil(r.data));
    api.get("/dashboard/aicte/flags?status=open").then((r) => setFlags(r.data));
  };
  useEffect(load, []);

  if (!overview) return <div>Loading...</div>;

  const pieData = [
    { name: "NRI", value: overview.nriCount },
    { name: "OCI", value: overview.ociCount },
    { name: "Foreign", value: overview.fnCount },
    { name: "Supernumerary", value: overview.superCount },
  ];
  const COLORS = ["#1e40af", "#16a34a", "#f97316", "#7c3aed"];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">AICTE Dashboard</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        {[
          ["Institutions", overview.institutions],
          ["Students", overview.students],
          ["Batches", overview.batches],
          ["Confirmed", overview.confirmed],
          ["Open Flags", overview.openFlags],
          ["High Flags", overview.highFlags],
          ["NRI", overview.nriCount],
          ["Supernumerary", overview.superCount],
        ].map(([l, v]) => (
          <Card key={l as string}><CardContent className="p-4">
            <div className="text-xs text-slate-500">{l}</div>
            <div className="text-2xl font-bold text-slate-800">{v}</div>
          </CardContent></Card>
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle>State Heatmap (students)</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-2">
            {(() => {
              const max = Math.max(...overview.byState.map((s: any) => s.students || 0), 1);
              return overview.byState.map((s: any) => {
                const intensity = (s.students || 0) / max;
                const bg = `rgba(30, 64, 175, ${0.15 + intensity * 0.75})`;
                return (
                  <div key={s.state} className="rounded-md p-3 text-center text-white" style={{ backgroundColor: bg }}>
                    <div className="text-xs font-medium">{s.state}</div>
                    <div className="text-lg font-bold">{s.students}</div>
                  </div>
                );
              });
            })()}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>Students by State</CardTitle></CardHeader>
          <CardContent className="h-64 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={overview.byState}>
                <XAxis dataKey="state" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="students" fill="#1e40af" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Category Mix</CardTitle></CardHeader>
          <CardContent className="h-64 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={90} label>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Flagged Institutions Queue</CardTitle></CardHeader>
        <CardContent>
          {flagged.length === 0 && <p className="text-sm text-slate-500">No flagged institutions.</p>}
          <table className="w-full text-sm">
            <thead className="bg-slate-100"><tr>
              <th className="px-2 py-1 text-left">Institution</th>
              <th className="px-2 py-1 text-left">State</th>
              <th className="px-2 py-1 text-left">Risk Score</th>
              <th className="px-2 py-1 text-left">Open Flags</th>
            </tr></thead>
            <tbody>
              {flagged.map((f: any) => (
                <tr key={f.id} className="border-t">
                  <td className="px-2 py-1">{f.name}</td>
                  <td className="px-2 py-1">{f.state}</td>
                  <td className="px-2 py-1"><Badge variant={f.risk_score >= 50 ? "destructive" : "warning"}>{f.risk_score}</Badge></td>
                  <td className="px-2 py-1">{f.open_flags}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Intake Utilisation</CardTitle></CardHeader>
        <CardContent>
          <div className="max-h-72 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 sticky top-0"><tr>
                <th className="px-2 py-1 text-left">Institution</th><th className="px-2 py-1 text-left">Programme</th>
                <th className="px-2 py-1 text-left">Branch</th><th className="px-2 py-1 text-left">Year</th>
                <th className="px-2 py-1 text-left">Used/Sanctioned</th><th className="px-2 py-1 text-left">Util %</th>
                <th className="px-2 py-1 text-left">Supernum</th>
              </tr></thead>
              <tbody>
                {util.map((u: any, i: number) => (
                  <tr key={i} className="border-t">
                    <td className="px-2 py-1">{u.name}</td>
                    <td className="px-2 py-1">{u.programme}</td>
                    <td className="px-2 py-1">{u.branch}</td>
                    <td className="px-2 py-1">{u.year}</td>
                    <td className="px-2 py-1">{u.used}/{u.sanctioned_intake}</td>
                    <td className="px-2 py-1">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-slate-200 rounded h-2">
                          <div className={`h-2 rounded ${u.utilisation > 100 ? "bg-red-500" : "bg-navy-500"}`} style={{ width: `${Math.min(100, u.utilisation)}%` }} />
                        </div>
                        <span className={u.utilisation > 100 ? "text-red-600 font-bold" : ""}>{u.utilisation}%</span>
                      </div>
                    </td>
                    <td className="px-2 py-1">{u.supernumeraryUsed}/{u.supernumerary_cap}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Open Flags</CardTitle></CardHeader>
        <CardContent>
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-100"><tr>
                <th className="px-2 py-1 text-left">Type</th><th className="px-2 py-1 text-left">Severity</th>
                <th className="px-2 py-1 text-left">Institution</th><th className="px-2 py-1 text-left">Reason</th><th className="px-2 py-1 text-left">Action</th>
              </tr></thead>
              <tbody>
                {flags.map((f: any) => (
                  <tr key={f.id} className="border-t">
                    <td className="px-2 py-1">{f.flag_type}</td>
                    <td className="px-2 py-1"><Badge variant={f.severity === "high" ? "destructive" : "warning"}>{f.severity}</Badge></td>
                    <td className="px-2 py-1">{f.institution_id}</td>
                    <td className="px-2 py-1 text-xs">{f.reason}</td>
                    <td className="px-2 py-1">
                      <Button size="sm" variant="ghost" onClick={async () => {
                        await api.post(`/dashboard/aicte/flags/${f.id}/resolve`, {});
                        setFlags(flags.filter((x) => x.id !== f.id));
                      }}>Resolve</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}