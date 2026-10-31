import { Navigate } from "react-router-dom";
export function Protected({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const tok = localStorage.getItem("token");
  if (!tok) return <Navigate to="/login" replace />;
  if (roles && roles.length) {
    try {
      const payload = JSON.parse(atob(tok.split(".")[1]));
      if (!roles.includes(payload.role)) return <Navigate to="/" replace />;
    } catch {
      return <Navigate to="/login" replace />;
    }
  }
  return <>{children}</>;
}