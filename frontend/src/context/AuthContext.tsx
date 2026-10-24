import React, { createContext, useContext, useState, useEffect } from "react";
import { User } from "../types";
import { api, setCsrfToken } from "../api/client";

interface AuthResponse extends User {
  csrf_token?: string;
  email?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  studentLogin: (roll_no: string, access_code: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkCurrentUser = async () => {
    try {
      setLoading(true);
      const res = await api.get<AuthResponse>("/api/auth/me");
      if (res && res.id) {
        setUser({
          id: res.id,
          username: res.username,
          role: res.role,
          student_id: res.student_id,
          company_id: res.company_id,
        });
        if (res.csrf_token) {
          setCsrfToken(res.csrf_token);
        }
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkCurrentUser();
  }, []);

  const login = async (username: string, password: string) => {
    setError(null);
    try {
      const res = await api.post<AuthResponse>("/api/auth/login", {
        username,
        password,
      });
      if (res && res.id) {
        setUser({
          id: res.id,
          username: res.username,
          role: res.role,
          student_id: res.student_id,
          company_id: res.company_id,
        });
        if (res.csrf_token) {
          setCsrfToken(res.csrf_token);
        }
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed.");
      throw err;
    }
  };

  const studentLogin = async (roll_no: string, access_code: string) => {
    setError(null);
    try {
      const res = await api.post<AuthResponse>("/api/auth/student-login", {
        roll_no,
        code: access_code,
      });
      if (res && res.id) {
        setUser({
          id: res.id,
          username: res.username,
          role: res.role,
          student_id: res.student_id,
          company_id: res.company_id,
        });
        if (res.csrf_token) {
          setCsrfToken(res.csrf_token);
        }
      }
    } catch (err: any) {
      setError(err.message || "Student authentication failed.");
      throw err;
    }
  };

  const logout = async () => {
    try {
      await api.post("/api/auth/logout", {});
    } catch {
      // Continue cleanup on failure
    } finally {
      setUser(null);
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        login,
        studentLogin,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
