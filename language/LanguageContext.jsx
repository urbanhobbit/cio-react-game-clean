// src/i18n/LanguageContext.jsx
import React, { createContext, useContext, useState, useMemo } from "react";
import tr from "../locales/tr.json";
import en from "../locales/en.json";

const LanguageContext = createContext(null);

const dictionaries = { tr, en };

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(
    () => localStorage.getItem("lang") || "tr"
  );

  const setLang = (newLang) => {
    setLangState(newLang);
    try {
      localStorage.setItem("lang", newLang);
    } catch (e) {
      // sessizce geç
    }
  };

  const value = useMemo(
    () => ({
      lang,
      setLang,
      t: (key) => dictionaries[lang]?.[key] ?? key,
    }),
    [lang]
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useLanguage, LanguageProvider içinde kullanılmalı.");
  }
  return ctx;
}
