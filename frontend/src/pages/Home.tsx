import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Button } from "../components/ui";
import { Upload, BarChart3, Building2, Users, ShieldCheck, ScrollText, FileText } from "lucide-react";

export function Home() {
  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-navy-900 to-navy-600 text-white rounded-xl p-8">
        <h2 className="text-3xl font-bold">AICTE-SETU</h2>
        <p className="mt-2 text-navy-100">APAAR-based Student Data Management & Verification System</p>
        <p className="mt-4 text-sm text-navy-200 max-w-3xl">
          Institutions submit student-level data keyed by APAAR ID. Automated validation, anomaly detection,
          real-time dashboards, consent-based verification, and tamper-evident records.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { to: "/upload", icon: Upload, title: "Upload", desc: "CSV / API upload with validation" },
          { to: "/dashboard", icon: BarChart3, title: "Dashboard", desc: "AICTE national & regional view" },
          { to: "/institutions", icon: Building2, title: "Institutions", desc: "Intake & utilisation" },
          { to: "/students", icon: Users, title: "Students", desc: "Records, credentials, consent" },
          { to: "/reports", icon: FileText, title: "Reports", desc: "Exportable analytics" },
          { to: "/audit", icon: ScrollText, title: "Audit", desc: "Immutable trail" },
          { to: "/login", icon: ShieldCheck, title: "Login", desc: "RBAC + mock OTP/MFA" },
        ].map(({ to, icon: Icon, title, desc }) => (
          <Link key={to} to={to} className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 hover:shadow-md transition">
            <Icon className="text-navy-600 mb-3" />
            <h3 className="font-semibold">{title}</h3>
            <p className="text-sm text-slate-500 mt-1">{desc}</p>
          </Link>
        ))}
      </div>
      <Card>
        <CardHeader><CardTitle>Guided demo story</CardTitle></CardHeader>
        <CardContent>
          <ol className="list-decimal list-inside space-y-1 text-sm text-slate-700">
            <li>Login as Institution Nodal (nodal@inst001.edu / inst123). Upload <code>sample_valid.csv</code> — validation report shows issues.</li>
            <li>Confirm a clean batch; dashboard updates in real time.</li>
            <li>Login as AICTE Admin — breach of approved intake triggers an alert with explanation.</li>
            <li>Cross-institution duplicate enrolment is detected and flagged.</li>
            <li>Employer requests verification, student consents, verifier sees limited verified data via QR.</li>
            <li>Audit log shows the full trail.</li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}