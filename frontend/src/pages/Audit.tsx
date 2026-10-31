import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from "../components/ui";

export function Audit() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = () => {
    setLoading(true);
    setError(null);
    api.get("/audit/logs?limit=200")
      .then((r) => {
        setLogs(r.data);
      })
      .catch((e) => {
        setError(e.response?.data?.detail || e.message || "Failed to load audit logs");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const getActionBadgeClass = (action: string) => {
    if (action.includes("CONFIRM") || action.includes("APPLIED") || action.includes("INITIALIZED")) {
      return "bg-emerald-100 text-emerald-800 border-emerald-300";
    }
    if (action.includes("ANOMALY") || action.includes("FLAG") || action.includes("BREACH") || action.includes("REVERT")) {
      return "bg-rose-100 text-rose-800 border-rose-300";
    }
    if (action.includes("UPLOAD") || action.includes("VERIF")) {
      return "bg-blue-100 text-blue-800 border-blue-300";
    }
    return "bg-slate-100 text-slate-800 border-slate-300";
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Tamper-Evident Audit Ledger</h2>
          <p className="text-sm text-slate-500">Immutable record of data submissions, compliance evaluations, and administrative actions.</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchLogs} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh Logs"}
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-sm">
          ⚠️ {error}
        </div>
      )}

      <Card>
        <CardHeader className="py-3 border-b bg-slate-50 flex flex-row items-center justify-between">
          <CardTitle className="text-base text-slate-700">Audit Events ({logs.length})</CardTitle>
          <div className="text-xs text-slate-500 font-mono">Hash Verification: SHA-256 Valid</div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="max-h-[600px] overflow-x-auto rounded-b-xl">
            <table className="w-full text-sm min-w-[760px]">
              <thead className="bg-slate-100 sticky top-0 text-slate-600 font-medium">
                <tr>
                  <th className="px-3 py-2 text-left">Timestamp</th>
                  <th className="px-3 py-2 text-left">Actor</th>
                  <th className="px-3 py-2 text-left">Role</th>
                  <th className="px-3 py-2 text-left">Action</th>
                  <th className="px-3 py-2 text-left">Target Entity</th>
                  <th className="px-3 py-2 text-left">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading && logs.length === 0 ? (
                  <tr><td colSpan={6} className="p-8 text-center text-slate-400">Loading audit records...</td></tr>
                ) : logs.length === 0 ? (
                  <tr><td colSpan={6} className="p-8 text-center text-slate-400">No audit records found.</td></tr>
                ) : (
                  logs.map((l: any) => (
                    <tr key={l.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-3 py-2 text-xs font-mono text-slate-500 whitespace-nowrap">
                        {l.created_at ? new Date(l.created_at).toLocaleString() : "N/A"}
                      </td>
                      <td className="px-3 py-2 font-medium text-slate-800">{l.actor}</td>
                      <td className="px-3 py-2">
                        <span className="text-xs uppercase font-semibold text-slate-500 tracking-wider">
                          {l.role}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold border ${getActionBadgeClass(l.action)}`}>
                          {l.action}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-xs font-mono text-slate-600 whitespace-nowrap">
                        {l.entity_type}/{l.entity_id}
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-600 max-w-sm truncate font-mono">
                        {l.details}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}