import { useCallback, useEffect, useRef, useState } from "react";
import type { AccountRole, AuthSnapshot } from "../../types/access";
import { authAPI } from "./api";

export function useAuth() {
  const [session, setSession] = useState<AuthSnapshot>({
    user: null,
    legacy_enabled: false,
    quick_login_roles: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const sequence = useRef(0);
  const mutating = useRef(false);
  const refresh = useCallback(async () => {
    if (mutating.current) return;
    const id = ++sequence.current;
    try {
      const value = await authAPI.me();
      if (id === sequence.current) {
        setSession(value);
        setError(null);
      }
    } catch (issue) {
      if (id === sequence.current)
        setError(
          issue instanceof Error
            ? issue.message
            : "Chưa kết nối được hệ thống.",
        );
    } finally {
      if (id === sequence.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => void refresh(), 0);
    const focus = () => void refresh();
    const expired = () => {
      ++sequence.current;
      setSession((value) => ({ ...value, user: null }));
      setLoading(false);
    };
    window.addEventListener("focus", focus);
    window.addEventListener("lens:auth-expired", expired);
    const invalidate = () => {
      ++sequence.current;
    };
    return () => {
      clearTimeout(timer);
      invalidate();
      window.removeEventListener("focus", focus);
      window.removeEventListener("lens:auth-expired", expired);
    };
  }, [refresh]);
  async function signIn(load: () => Promise<AuthSnapshot>) {
    if (mutating.current)
      throw new Error("Đang xử lý đăng nhập. Vui lòng đợi.");
    mutating.current = true;
    ++sequence.current;
    try {
      const value = await load();
      ++sequence.current;
      setSession(value);
      setError(null);
      setLoading(false);
    } finally {
      mutating.current = false;
    }
  }
  const login = (username: string, password: string) =>
    signIn(() => authAPI.login(username, password));
  const quickLogin = (role: AccountRole) =>
    signIn(() => authAPI.quickLogin(role));
  async function logout() {
    mutating.current = true;
    ++sequence.current;
    try {
      await authAPI.logout();
      ++sequence.current;
      setSession((value) => ({ ...value, user: null }));
      setLoading(false);
    } finally {
      mutating.current = false;
    }
  }
  return { ...session, loading, error, refresh, login, quickLogin, logout };
}
