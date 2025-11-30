import React, { createContext, useContext, useState, useMemo } from "react";
import { translations } from "./i18n";

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(localStorage.getItem("lang") || "en");

  const value = useMemo(() => {
    const t = translations[lang];
    return { lang, t, setLang: (l) => {
      localStorage.setItem("lang", l);
      setLang(l);
    }};
  }, [lang]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLang() {
  return useContext(LanguageContext);
}
