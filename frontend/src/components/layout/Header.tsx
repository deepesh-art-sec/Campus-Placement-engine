import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  Bell,
  ChevronDown,
  LogOut,
  HelpCircle,
  Inbox,
  User,
  Zap,
  Check,
  ShieldAlert,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../api/client";
import { useCorporateTheme, THEME_OPTIONS, CyberTheme } from "../../context/ThemeContext";

interface HeaderProps {
  onOpenTour?: () => void;
  onNavigateToAudit?: () => void;
  onOpenMessageBox?: () => void;
  onOpenAlerts?: () => void;
  onSearchChange?: (query: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenTour,
  onOpenMessageBox,
  onOpenAlerts,
  onSearchChange,
}) => {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useCorporateTheme();
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [themeDropdownOpen, setThemeDropdownOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  
  const dropdownRef = useRef<HTMLDivElement>(null);
  const themeDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user?.role === "officer" || user?.role === "coordinator") {
      let active = true;
      const checkPending = () => {
        api.get<{ total_pending: number }>("/api/officer/inbox/summary")
          .then((res) => {
            if (active && res && typeof res.total_pending === "number") {
              setPendingCount(res.total_pending);
            }
          })
          .catch(() => {});
      };

      checkPending();
      const timer = setInterval(checkPending, 15000);
      return () => {
        active = false;
        clearInterval(timer);
      };
    }
  }, [user]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
      if (themeDropdownRef.current && !themeDropdownRef.current.contains(event.target as Node)) {
        setThemeDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchValue(e.target.value);
    if (onSearchChange) onSearchChange(e.target.value);
  };

  const currentTheme = THEME_OPTIONS.find((t) => t.id === theme) || THEME_OPTIONS[0];

  const displayRole = user?.role
    ? user.role === "coordinator"
      ? "Coordinator"
      : user.role === "officer"
      ? "Placement Officer"
      : user.role === "student"
      ? "Student"
      : "Recruiter"
    : "Coordinator";

  return (
    <header className="corporate-header sticky top-0 z-30 shadow-[0_4px_20px_rgba(0,0,0,0.6)] no-print shrink-0">
      <div className="w-full px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Left: Cyber Search Input */}
        <div className="relative w-72 sm:w-80 md:w-96 max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-cyan-400 opacity-70 pointer-events-none" />
          <input
            type="text"
            value={searchValue}
            onChange={handleSearch}
            placeholder="Search companies, students, or drives..."
            className="w-full pl-9 pr-4 py-2 text-xs font-medium focus:outline-none focus:ring-2 shadow-xs placeholder-slate-500"
          />
        </div>

        {/* Right: Cyber Theme Switcher, Notifications & User Profile */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Cyber Theme Dropdown */}
          <div className="relative" ref={themeDropdownRef}>
            <button
              type="button"
              onClick={() => setThemeDropdownOpen(!themeDropdownOpen)}
              className="flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl border border-[#16264C] hover:border-cyan-400/80 bg-[#0A1122] hover:bg-[#101C38] text-xs font-semibold cursor-pointer shadow-xs transition-all text-slate-200"
              title="Change Cyber Dark Color Combination"
            >
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              <div className="flex items-center gap-1 hidden sm:flex">
                {currentTheme.previewColors.map((color, idx) => (
                  <span
                    key={idx}
                    className="w-2.5 h-2.5 rounded-full ring-1 ring-white/10 shrink-0"
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
              <span className="text-[11px] font-bold text-white hidden md:inline truncate max-w-[110px]">
                {currentTheme.name}
              </span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {/* Dropdown Menu for 4 Cyber Combinations */}
            {themeDropdownOpen && (
              <div className="absolute right-0 mt-2 w-72 corporate-card shadow-2xl p-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="px-3 py-2 border-b border-[#16264C]">
                  <span className="text-[10px] font-black uppercase tracking-wider text-cyan-400 block">
                    Cyber Dark Palette
                  </span>
                  <p className="text-xs font-extrabold text-white mt-0.5">
                    4 High-Tech Color Combinations
                  </p>
                </div>

                <div className="py-1 space-y-1">
                  {THEME_OPTIONS.map((opt) => {
                    const isSelected = theme === opt.id;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => {
                          setTheme(opt.id);
                          setThemeDropdownOpen(false);
                        }}
                        className={`w-full text-left p-2.5 rounded-xl flex items-center justify-between transition-all cursor-pointer ${
                          isSelected
                            ? "bg-cyan-950/60 border border-cyan-500/80 text-white font-bold shadow-[0_0_15px_rgba(0,240,255,0.2)]"
                            : "hover:bg-[#101C38] border border-transparent text-slate-300"
                        }`}
                      >
                        <div className="space-y-1 min-w-0 pr-2">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-bold leading-tight truncate text-white">
                              {opt.name}
                            </span>
                            <span className="text-[9px] px-1.5 py-0.2 rounded-full font-bold uppercase tracking-wider bg-cyan-950 text-cyan-300 border border-cyan-700/60">
                              Cyber
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-400 block truncate leading-none">
                            {opt.tagline}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {/* 4 Color Dots */}
                          <div className="flex items-center -space-x-1">
                            {opt.previewColors.map((col, cIdx) => (
                              <span
                                key={cIdx}
                                className="w-3.5 h-3.5 rounded-full ring-2 ring-[#0B1326] shrink-0 shadow-2xs"
                                style={{ backgroundColor: col }}
                              />
                            ))}
                          </div>
                          {isSelected && (
                            <Check className="w-4 h-4 text-cyan-400 shrink-0 ml-1" />
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Notifications Bell with Red Alert Dot */}
          <button
            type="button"
            onClick={() => onOpenAlerts ? onOpenAlerts() : onOpenMessageBox ? onOpenMessageBox() : null}
            className="relative p-2 rounded-xl border border-[#16264C] hover:border-cyan-400/60 bg-[#0A1122] hover:bg-[#101C38] transition-all cursor-pointer text-slate-300 hover:text-white"
            title="Notifications & Alerts"
          >
            <Bell className="w-4.5 h-4.5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full ring-2 ring-[#080E1C] shadow-[0_0_8px_#F43F5E]" />
          </button>

          {/* User Profile with Dropdown */}
          {user && (
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-2 pl-1.5 pr-2 py-1.5 rounded-xl hover:bg-[#101C38] transition-all cursor-pointer border border-[#16264C] hover:border-cyan-400/60 bg-[#0A1122]"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-cyan-500 text-white flex items-center justify-center text-xs font-black shadow-sm ring-2 ring-cyan-500/30">
                  <User className="w-4 h-4 text-white" />
                </div>
                <div className="text-left hidden sm:block">
                  <span className="text-xs font-bold text-white block leading-tight">
                    {displayRole}
                  </span>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {/* Profile Dropdown Menu */}
              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 corporate-card shadow-2xl py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="px-4 py-2 border-b border-[#16264C]">
                    <p className="text-xs font-bold text-white truncate">
                      {user.username}
                    </p>
                    <p className="text-[11px] text-cyan-400 font-semibold capitalize">
                      {user.role.replace("_", " ")}
                    </p>
                  </div>

                  {onOpenMessageBox && user?.role === "officer" && (
                    <button
                      type="button"
                      onClick={() => {
                        setDropdownOpen(false);
                        onOpenMessageBox();
                      }}
                      className="w-full text-left px-4 py-2 text-xs font-medium text-slate-300 hover:bg-[#101C38] hover:text-white flex items-center gap-2 transition-colors cursor-pointer"
                    >
                      <Inbox className="w-4 h-4 text-cyan-400" />
                      Message Box
                      {pendingCount > 0 && (
                        <span className="ml-auto px-1.5 py-0.2 bg-amber-500 text-white text-[9px] font-bold rounded-full">
                          {pendingCount}
                        </span>
                      )}
                    </button>
                  )}

                  {onOpenTour && user?.role !== "student" && (
                    <button
                      type="button"
                      onClick={() => {
                        setDropdownOpen(false);
                        onOpenTour();
                      }}
                      className="w-full text-left px-4 py-2 text-xs font-medium text-slate-300 hover:bg-[#101C38] hover:text-white flex items-center gap-2 transition-colors cursor-pointer"
                    >
                      <HelpCircle className="w-4 h-4 text-cyan-400" />
                      Guided Tour
                    </button>
                  )}

                  <div className="border-t border-[#16264C] my-1" />

                  <button
                    type="button"
                    onClick={() => {
                      setDropdownOpen(false);
                      logout();
                    }}
                    className="w-full text-left px-4 py-2 text-xs font-medium text-rose-400 hover:bg-rose-950/40 flex items-center gap-2 transition-colors cursor-pointer"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
