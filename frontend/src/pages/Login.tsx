import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from "../components/ui";
import { loginApi, verifyOtp, setToken } from "../lib/api";

const DEMO = [
  { email: "admin@aicte.gov.in", pw: "admin123", role: "AICTE Admin" },
  { email: "regional@aicte.gov.in", pw: "regional123", role: "Regional Officer" },
  { email: "nodal@inst001.edu", pw: "inst123", role: "Institution Nodal" },
  { email: "verifier@company.com", pw: "verifier123", role: "Verifier" },
  { email: "auditor@aicte.gov.in", pw: "auditor123", role: "Auditor" },
];

export function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("admin@aicte.gov.in");
  const [password, setPassword] = useState("admin123");
  const [sessionId, setSessionId] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState<"creds" | "otp">("creds");
  const [err, setErr] = useState("");

  const doLogin = async (e: any) => {
    e.preventDefault();
    setErr("");
    try {
      const r = await loginApi(email, password);
      setSessionId(r.session_id);
      setOtp(r.demo_otp);
      setStep("otp");
    } catch (e: any) {
      setErr(e.response?.data?.detail || e.message);
    }
  };

  const doOtp = async (e: any) => {
    e.preventDefault();
    setErr("");
    try {
      const r = await verifyOtp(sessionId, otp);
      setToken(r.access_token);
      nav("/");
    } catch (e: any) {
      setErr(e.response?.data?.detail || e.message);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-12">
      <Card>
        <CardHeader><CardTitle>Sign in (mock OTP/MFA)</CardTitle></CardHeader>
        <CardContent>
          {step === "creds" ? (
            <form onSubmit={doLogin} className="space-y-4">
              <div><Label>Email</Label><Input value={email} onChange={(e: any) => setEmail(e.target.value)} /></div>
              <div><Label>Password</Label><Input type="password" value={password} onChange={(e: any) => setPassword(e.target.value)} /></div>
              {err && <div className="text-red-600 text-sm">{err}</div>}
              <Button type="submit" className="w-full">Continue</Button>
            </form>
          ) : (
            <form onSubmit={doOtp} className="space-y-4">
              <div><Label>OTP (demo: {otp})</Label><Input value={otp} onChange={(e: any) => setOtp(e.target.value)} /></div>
              {err && <div className="text-red-600 text-sm">{err}</div>}
              <Button type="submit" className="w-full">Verify & Sign in</Button>
            </form>
          )}
        </CardContent>
      </Card>
      <Card className="mt-4">
        <CardHeader><CardTitle>Demo accounts</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full text-xs">
            <thead><tr><th className="text-left">Role</th><th className="text-left">Email</th><th className="text-left">Password</th></tr></thead>
            <tbody>
              {DEMO.map((d) => (
                <tr key={d.email} className="border-t cursor-pointer hover:bg-slate-50" onClick={() => { setEmail(d.email); setPassword(d.pw); }}>
                  <td className="py-1">{d.role}</td><td>{d.email}</td><td>{d.pw}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}