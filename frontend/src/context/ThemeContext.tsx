import React, { createContext, useContext, useState, useEffect } from "react";

export type CyberTheme =
  | "cyber-neon"        // 1. Cyber Neon (Cyan & Electric Blue - Default)
  | "cyber-sapphire"    // 2. Cyber Sapphire (Deep Space & Cobalt)
  | "cyber-matrix"      // 3. Cyber Matrix (Emerald Tech & Obsidian)
  | "cyber-synthwave";  // 4. Cyber Synthwave (Violet Plasma & Neon Purple)

export interface ThemeOption {
  id: CyberTheme;
  name: string;
  tagline: string;
  type: "dark";
  previewColors: string[];
}

export const THEME_OPTIONS: ThemeOption[] = [
  {
    id: "cyber-neon",
    name: "Cyber Neon",
    tagline: "Electric Cyan & Blue",
    type: "dark",
    previewColors: ["#060B16", "#0B1326", "#00F0FF", "#2563EB"],
  },
  {
    id: "cyber-sapphire",
    name: "Cyber Sapphire",
    tagline: "Deep Space & Cobalt",
    type: "dark",
    previewColors: ["#050814", "#091024", "#3B82F6", "#60A5FA"],
  },
  {
    id: "cyber-matrix",
    name: "Cyber Matrix",
    tagline: "Emerald Tech & Obsidian",
    type: "dark",
    previewColors: ["#04090A", "#081418", "#00FF9D", "#10B981"],
  },
  {
    id: "cyber-synthwave",
    name: "Cyber Synthwave",
    tagline: "Violet Plasma & Purple",
    type: "dark",
    previewColors: ["#080612", "#110D24", "#C084FC", "#A855F7"],
  },
];

interface ThemeContextType {
  theme: CyberTheme;
  setTheme: (theme: CyberTheme) => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: "cyber-neon",
  setTheme: () => {},
  isDark: true,
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<CyberTheme>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("im101_theme") as CyberTheme;
      if (saved && ["cyber-neon", "cyber-sapphire", "cyber-matrix", "cyber-synthwave"].includes(saved)) {
        return saved;
      }
    }
    return "cyber-neon";
  });

  const setTheme = (newTheme: CyberTheme) => {
    setThemeState(newTheme);
    if (typeof window !== "undefined") {
      localStorage.setItem("im101_theme", newTheme);
      document.documentElement.setAttribute("data-theme", newTheme);
      document.documentElement.classList.add("dark");
    }
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      document.documentElement.setAttribute("data-theme", theme);
      document.documentElement.classList.add("dark");
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, isDark: true }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useCorporateTheme = () => useContext(ThemeContext);
