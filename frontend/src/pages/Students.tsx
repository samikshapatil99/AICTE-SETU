import { useEffect, useState } from "react";
import { api, downloadFile } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle, Button, Input, Label, Select } from "../components/ui";
import { QRCodeSVG } from "qrcode.react";

export function Students() {
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [instId, setInstId] = useState("");
  const [students, setStudents] = useState<any[]>([]);
  const [cred, setCred] = useState<any>(null);
  const [verifyReq, setVerifyReq] = useState<any>(null);
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [apaar, setApaar] = useState("");

  useEffect(() => { api.get("/institutions").then((r) => { setInstitutions(r.data); if (r.data.length) setInstId(r.data[0].id); }); }, []);
  useEffect(() => { if (instId) api.get(`/students?institution_id=${instId}`).then((r) => setStudents(r.data)); }, [instId]);

  const issueCred = async (sid: string) => {
    const r = await api.post(`/students/${sid}/credential`, {});
    setCred(r.data);
  };

  const requestVerification = async (a: string) => {
    const r = await api.post("/verification/request", { apaar_id: a, requester: "Employer Demo", purpose: "Background check", fields: ["name", "institution_id", "programme", "status"] });
    setVerifyReq(r.data);
    setVerifyResult(null);
  };

  const grantConsent = async () => {
    if (!verifyReq) return;
    await api.post(`/verification/consent/${verifyReq.requestId}`, { granted: true, fields: ["name", "institution_id", "programme", "status"] });
    const r = await api.get(`/verification/result/${verifyReq.requestId}`);
    setVerifyResult(r.data);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Students & Verification</h2>
      <div className="flex items-center gap-3">
        <Label>Institution:</Label>
        <Select value={instId} onChange={(e: any) => setInstId(e.target.value)}>
          {institutions.map((i: any) => <option key={i.id} value={i.id}>{i.name}</option>)}
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="hidden md:block max-h-[420px] overflow-x-auto rounded-xl border">
            <table className="w-full text-sm min-w-[720px]">
              <thead className="bg-slate-100 sticky top-0">
                <tr><th className="px-2 py-1 text-left">Name</th><th className="px-2 py-1 text-left">APAAR</th><th className="px-2 py-1 text-left">Programme</th><th className="px-2 py-1 text-left">Branch</th><th className="px-2 py-1 text-left">Year</th><th className="px-2 py-1 text-left">Status</th><th className="px-2 py-1 text-left">Actions</th></tr>
              </thead>
              <tbody>
                {students.map((s: any) => (
                  <tr key={s.id} className="border-t">
                    <td className="px-2 py-1">{s.name}</td>
                    <td className="px-2 py-1 text-xs">{s.apaar_id}</td>
                    <td className="px-2 py-1">{s.programme}</td>
                    <td className="px-2 py-1">{s.branch}</td>
                    <td className="px-2 py-1">{s.year}</td>
                    <td className="px-2 py-1">{s.status}</td>
                    <td className="px-2 py-1 space-x-2">
                      <button onClick={() => issueCred(s.id)} className="text-xs text-navy-600 hover:underline">Issue Credential</button>
                      <button onClick={() => downloadFile(`/students/${s.id}/certificate.pdf`, `certificate_${s.id}.pdf`)} className="text-xs text-purple-600 hover:underline">Certificate PDF</button>
                      <button onClick={() => requestVerification(s.apaar_id)} className="text-xs text-green-600 hover:underline">Request Verify</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="md:hidden p-4 space-y-3">
            {students.map((s: any) => (
              <div key={s.id} className="border rounded-lg p-3 space-y-1">
                <div className="font-medium">{s.name}</div>
                <div className="text-xs text-slate-500">{s.apaar_id}</div>
                <div className="text-xs">{s.programme} · {s.branch} · {s.year}</div>
                <div className="text-xs">Status: {s.status}</div>
                <div className="flex gap-2 mt-2">
                  <button onClick={() => issueCred(s.id)} className="text-xs text-navy-600 underline">Issue Credential</button>
                  <button onClick={() => requestVerification(s.apaar_id)} className="text-xs text-green-600 underline">Request Verify</button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {cred && (
        <Card>
          <CardContent className="flex flex-col md:flex-row gap-6 items-center p-6">
            <QRCodeSVG value={window.location.origin + cred.verifyUrl} size={160} />
            <div className="space-y-2">
              <h3 className="font-semibold">Verifiable Credential Issued</h3>
              <p className="text-sm text-slate-600">Credential ID: {cred.credentialId}</p>
              <p className="text-sm text-slate-600">Hash: {cred.hash.slice(0, 24)}...</p>
              <a href={cred.verifyUrl} target="_blank" rel="noreferrer" className="text-sm text-navy-600 hover:underline">Open verification page →</a>
            </div>
          </CardContent>
        </Card>
      )}

      {verifyReq && (
        <Card>
          <CardHeader><CardTitle>Consent-based Verification Demo</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-slate-600">Request ID: {verifyReq.requestId}</p>
            <p className="text-sm text-slate-600">Requester: Employer Demo · Purpose: Background check</p>
            <Button onClick={grantConsent}>Grant Consent (Student) & Execute</Button>
            {verifyResult && <pre className="bg-slate-50 p-3 rounded text-xs overflow-auto">{JSON.stringify(verifyResult, null, 2)}</pre>}
          </CardContent>
        </Card>
      )}
    </div>
  );
}