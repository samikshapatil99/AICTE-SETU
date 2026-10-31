import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { GraduationCap, Upload, BarChart3, Building2, Users, ShieldCheck, FileText, ScrollText, LogIn, Languages, Menu, X } from "lucide-react";
import { useLang } from "../i18n";

const nav = [
  { to: "/", key: "home", icon: GraduationCap },
  { to: "/upload", key: "upload", icon: Upload },
  { to: "/dashboard", key: "dashboard", icon: BarChart3 },
  { to: "/institutions", key: "institutions", icon: Building2 },
  { to: "/students", key: "students", icon: Users },
  { to: "/reports", key: "reports", icon: FileText },
  { to: "/cases", key: "cases", icon: ShieldCheck },
  { to: "/replay", key: "replay", icon: BarChart3 },
  { to: "/recovery", key: "recovery", icon: Upload },
  { to: "/simulator", key: "simulator", icon: Users },
  { to: "/audit", key: "audit", icon: ScrollText },
  { to: "/login", key: "login", icon: LogIn },
];

export function Layout({ children }: { children?: React.ReactNode }) {
  const { lang, setLang, t } = useLang();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  // close drawer on navigation
  // (handled by onClick on links)

  return (
    <div className="min-h-dvh flex">
      {/* overlay */}
      {open && <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setOpen(false)} aria-hidden="true" />}
      {/* sidebar */}
      <aside
        className={`fixed z-40 inset-y-0 left-0 w-64 bg-navy-900 text-white flex flex-col transform transition-transform duration-200 lg:static lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
        aria-label="Primary navigation"
      >
        <div className="px-5 py-6 border-b border-navy-700 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">{t("title")}</h1>
            <p className="text-xs text-navy-100 mt-1">{t("subtitle")}</p>
          </div>
          <button className="lg:hidden p-2 rounded hover:bg-navy-700" aria-label="Close menu" onClick={() => setOpen(false)}>
            <X size={18} />
          </button>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {nav.map(({ to, key, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"}
              onClick={() => setOpen(false)}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition ${isActive ? "bg-navy-600 text-white" : "text-navy-100 hover:bg-navy-700"}`}>
              <Icon size={18} /> <span className="truncate">{t(key) || key}</span>
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 border-t border-navy-700 flex items-center justify-between">
          <button onClick={() => setLang(lang === "en" ? "hi" : "en")} className="flex items-center gap-2 text-xs text-navy-100 hover:text-white">
            <Languages size={14} /> {lang === "en" ? "हिंदी" : "English"}
          </button>
          <span className="text-xs text-navy-200">v0.2</span>
        </div>
      </aside>
      <div className="flex-1 min-w-0 flex flex-col">
        {/* mobile header */}
        <header className="lg:hidden sticky top-0 z-20 bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3">
          <button className="p-2 rounded hover:bg-slate-100" aria-label="Open menu" onClick={() => setOpen(true)}>
            <Menu size={20} />
          </button>
          <span className="font-semibold text-navy-900 truncate">{t("title")}</span>
        </header>
        {/* banner */}
        <div className="bg-amber-50 border-b border-amber-200 text-amber-800 text-xs px-4 py-2 text-center">
          Synthetic data. Simulated APAAR lookup. Demo rules, not official AICTE policy.
        </div>
        <main className="flex-1 w-full min-w-0">
          <div className="mx-auto w-full max-w-7xl p-4 sm:p-6 min-w-0">
            {children ?? <Outlet />}
          </div>
        </main>
      </div>
    </div>
  );
}