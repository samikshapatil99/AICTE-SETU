import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LangProvider } from "./i18n";
import { ToastProvider } from "./components/Toast";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Upload } from "./pages/Upload";
import { Dashboard } from "./pages/Dashboard";
import { Institutions } from "./pages/Institutions";
import { Students } from "./pages/Students";
import { Verify } from "./pages/Verify";
import { Audit } from "./pages/Audit";
import { Reports } from "./pages/Reports";
import { Cases } from "./pages/Cases";
import { Replay } from "./pages/Replay";
import { Recovery } from "./pages/Recovery";
import { Simulator } from "./pages/Simulator";
import { Protected } from "./components/Protected";
import { ErrorBoundary } from "./components/ErrorBoundary";

export default function App() {
  return (
    <LangProvider>
      <ToastProvider>
      <Layout>
        <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/verify/:id" element={<Verify />} />
          <Route path="/upload" element={<Protected><Upload /></Protected>} />
          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="/institutions" element={<Protected><Institutions /></Protected>} />
          <Route path="/students" element={<Protected><Students /></Protected>} />
          <Route path="/audit" element={<Protected><Audit /></Protected>} />
          <Route path="/reports" element={<Protected><Reports /></Protected>} />
          <Route path="/cases" element={<Protected><Cases /></Protected>} />
          <Route path="/replay" element={<Protected><Replay /></Protected>} />
          <Route path="/recovery" element={<Protected><Recovery /></Protected>} />
          <Route path="/simulator" element={<Protected><Simulator /></Protected>} />
        </Routes>
        </ErrorBoundary>
      </Layout>
      </ToastProvider>
    </LangProvider>
  );
}