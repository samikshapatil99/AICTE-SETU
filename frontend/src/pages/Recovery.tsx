import { useEffect, useState, useRef } from "react";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from "../components/ui";

export function Recovery() {
  const [issues, setIssues] = useState<any[]>([]);
  const [trend, setTrend] = useState<any[]>([]);
  const [preview, setPreview] = useState<any>(null);
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [appliedStatus, setAppliedStatus] = useState<string | null>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  const load = () => {
    setLoading(true);
    api.get("/compliance/recovery/plan")
      .then((r) => setIssues(r.data))
      .catch((err) => console.error("Error loading recovery plan:", err))
      .finally(() => setLoading(false));
    api.get("/compliance/recovery/trend").then((r) => setTrend(r.data)).catch(() => {});
  };
  useEffect(load, []);

  const doPreview = async (issueId: string) => {
    setPreviewingId(issueId);
    setAppliedStatus(null);
    try {
      const r = await api.post("/compliance/recovery/normalise-preview", {
        issue_id: issueId,
        proposed: { quota: "Management / NRI", social_category: "General", status: "admitted" }
      });
      setPreview(r.data);
      setTimeout(() => {
        previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    } catch (e: any) {
      alert("Preview error: " + (e.response?.data?.detail || e.message));
    } finally {
      setPreviewingId(null);
    }
  };

  const doApply = async (actionId: string) => {
    try {
      await api.post(`/compliance/recovery/apply/${actionId}`, {});
      setAppliedStatus("Applied successfully! State versioned in immutable audit ledger.");
      load();
    } catch (e: any) {
      alert("Apply error: " + (e.response?.data?.detail || e.message));
    }
  };

  const doRevert = async (actionId: string) => {
    try {
      await api.post(`/compliance/recovery/revert/${actionId}`, {});
      setAppliedStatus("Reverted successfully. Flag reopened.");
      load();
    } catch (e: any) {
      alert("Revert error: " + (e.response?.data?.detail || e.message));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Data Quality Recovery Planner</h2>
          <p className="text-sm text-slate-500">Autonomous remediation & reversible normalisation of flagged student records.</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh Issues"}
        </Button>
      </div>

      {/* Prominent Preview Fix Card at the Top */}
      {preview && (
        <div ref={previewRef} className="animate-in fade-in slide-in-from-top-4 duration-300">
          <Card className="border-2 border-indigo-500 bg-indigo-50/20 shadow-md">
            <CardHeader className="bg-indigo-50/50 pb-3 border-b">
              <div className="flex justify-between items-center">
                <CardTitle className="text-indigo-900 flex items-center gap-2">
                  <span>⚡ Reversible Normalisation Preview</span>
                  <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                    Non-Destructive Dry Run
                  </Badge>
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setPreview(null)}>✕ Close</Button>
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <div className="bg-white p-3 rounded-lg border">
                  <div className="text-xs text-slate-500">Target Student</div>
                  <div className="font-semibold text-slate-800">{preview.student_name || "Enrolled Student"}</div>
                  <div className="text-xs font-mono text-slate-600 mt-1">APAAR: {preview.apaar_id || "N/A"}</div>
                </div>
                <div className="bg-white p-3 rounded-lg border">
                  <div className="text-xs text-slate-500">Detected Reason</div>
                  <div className="text-xs font-medium text-rose-600 mt-1">{preview.reason || "Data inconsistency"}</div>
                </div>
                <div className="bg-white p-3 rounded-lg border">
                  <div className="text-xs text-slate-500">Recovery Action ID</div>
                  <div className="text-xs font-mono text-indigo-700 truncate mt-1">{preview.action_id}</div>
                  <div className="text-[11px] text-emerald-600 font-medium">Reversible at any time: YES</div>
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold text-slate-700 mb-1">Proposed Normalisation Changes:</div>
                <pre className="bg-slate-900 text-emerald-400 p-3 rounded-lg text-xs font-mono overflow-auto max-h-40">
                  {JSON.stringify(preview.preview, null, 2)}
                </pre>
              </div>

              {appliedStatus && (
                <div className="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-sm font-medium">
                  ✓ {appliedStatus}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4" onClick={() => doApply(preview.action_id)}>
                  ✓ Apply Fix (Versioned)
                </Button>
                <Button size="sm" variant="outline" className="border-slate-300" onClick={() => doRevert(preview.action_id)}>
                  ↺ Revert Fix
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader><CardTitle>Prioritised Issues ({issues.length} Open)</CardTitle></CardHeader>
        <CardContent>
          <div className="max-h-[500px] overflow-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-left">Severity</th>
                  <th className="px-3 py-2 text-left">Priority</th>
                  <th className="px-3 py-2 text-left">Target / Reason</th>
                  <th className="px-3 py-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {issues.length === 0 ? (
                  <tr><td colSpan={5} className="p-4 text-center text-slate-400">No open compliance issues found.</td></tr>
                ) : (
                  issues.map((i: any) => (
                    <tr key={i.id} className="border-t hover:bg-slate-50 transition-colors">
                      <td className="px-3 py-2">
                        <Badge variant="outline" className="text-xs capitalize">{i.type?.replace("_", " ")}</Badge>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                          i.severity === "high" ? "bg-rose-100 text-rose-700" :
                          i.severity === "medium" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-700"
                        }`}>
                          {i.severity}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-bold text-slate-700">{i.priority}</td>
                      <td className="px-3 py-2 text-xs">
                        <div className="font-medium text-slate-800">{i.student_name ? `${i.student_name} (${i.apaar_id || ""})` : i.flag_type}</div>
                        <div className="text-slate-500">{i.reason}</div>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <Button
                          size="sm"
                          className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
                          disabled={previewingId === i.id}
                          onClick={() => doPreview(i.id)}
                        >
                          {previewingId === i.id ? "Loading..." : "Preview Fix"}
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500 mt-3">Priority score = severity (10/20/30) + downstream impact (×5, max 40) + urgency (0/10/20). Fully explainable formula.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Resolved Issues Trend (Last 7 Days)</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead className="bg-slate-100"><tr><th className="px-3 py-2 text-left">Date</th><th className="px-3 py-2 text-left">Resolved Count</th></tr></thead>
            <tbody>
              {trend.length === 0 ? (
                <tr><td colSpan={2} className="p-3 text-center text-slate-400">No resolved issues yet.</td></tr>
              ) : (
                trend.map((t: any, idx: number) => (
                  <tr key={idx} className="border-t">
                    <td className="px-3 py-2 text-xs font-mono">{t.date}</td>
                    <td className="px-3 py-2 font-semibold text-emerald-600">{t.resolved}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}