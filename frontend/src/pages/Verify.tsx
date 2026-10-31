import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { QRCodeSVG } from "qrcode.react";
import { ShieldCheck, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent } from "../components/ui";

export function Verify() {
  const { id } = useParams();
  const [cred, setCred] = useState<any>(null);
  const [verify, setVerify] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/verification/credential/${id}`).then((r) => {
      setCred(r.data);
      return api.post(`/verification/credential/${id}/verify`, {});
    }).then((r) => setVerify(r.data)).catch((e) => setError(e.response?.data?.detail || e.message));
  }, [id]);

  if (error) return <div className="text-red-600">{error}</div>;
  if (!cred) return <div>Loading credential...</div>;

  return (
    <div className="max-w-xl mx-auto">
      <Card>
        <CardContent className="p-8 space-y-4 text-center">
          <ShieldCheck className="mx-auto text-navy-600" size={48} />
          <h2 className="text-2xl font-bold text-slate-800">Credential Verification</h2>
          <div className="flex justify-center"><QRCodeSVG value={window.location.href} size={140} /></div>
          <div className="text-left space-y-1 text-sm">
            <div><b>APAAR ID:</b> {cred.apaar_id}</div>
            <div><b>Name:</b> {cred.payload?.name}</div>
            <div><b>Institution:</b> {cred.institution_id}</div>
            <div><b>Programme:</b> {cred.payload?.programme} · {cred.payload?.branch}</div>
            <div><b>Year:</b> {cred.payload?.year}</div>
            <div><b>Status:</b> {cred.payload?.status}</div>
            <div className="text-xs text-slate-500">Issued: {cred.issued_at}</div>
            <div className="text-xs text-slate-500 break-all">Hash: {cred.hash}</div>
          </div>
          <div className="flex items-center justify-center gap-2 text-sm">
            {verify?.valid ? <><CheckCircle className="text-green-600" /> <span className="text-green-600 font-semibold">Integrity Verified</span></> : <><XCircle className="text-red-600" /> <span className="text-red-600 font-semibold">Tampered / Invalid</span></>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}