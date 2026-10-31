import React, { createContext, useContext, useState, useCallback } from "react";
type Toast = { id: number; msg: string; kind: "success" | "error" | "info" };
const Ctx = createContext<{ push: (msg: string, kind?: Toast["kind"]) => void }>({ push: () => {} });
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((msg: string, kind: Toast["kind"] = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, msg, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
  }, []);
  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2">
        {toasts.map((t) => (
          <div key={t.id} className={`px-4 py-2 rounded-md shadow text-sm text-white ${t.kind === "error" ? "bg-red-600" : t.kind === "success" ? "bg-green-600" : "bg-navy-700"}`}>
            {t.msg}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
export const useToast = () => useContext(Ctx);