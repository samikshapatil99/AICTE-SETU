import React, { createContext, useContext, useState } from "react";

const dict: Record<string, Record<string, string>> = {
  en: {
    home: "Home", upload: "Upload", dashboard: "Dashboard", institutions: "Institutions",
    students: "Students", verify: "Verify", audit: "Audit", reports: "Reports", login: "Login",
    title: "AICTE-SETU", subtitle: "APAAR-based Student Data Management & Verification",
  },
  hi: {
    home: "होम", upload: "अपलोड", dashboard: "डैशबोर्ड", institutions: "संस्थान",
    students: "छात्र", verify: "सत्यापन", audit: "ऑडिट", reports: "रिपोर्ट", login: "लॉगिन",
    title: "एआईसीटीई-सेतु", subtitle: "एपीएएआर आधारित छात्र डेटा प्रबंधन एवं सत्यापन",
  },
};

const Ctx = createContext<{ lang: string; setLang: (l: string) => void; t: (k: string) => string }>({ lang: "en", setLang: () => {}, t: (k) => k });

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState("en");
  const t = (k: string) => dict[lang]?.[k] ?? dict.en[k] ?? k;
  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}
export const useLang = () => useContext(Ctx);