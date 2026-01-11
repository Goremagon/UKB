import { useEffect, useMemo, useState } from "react";
import { Shield, User } from "lucide-react";

import api, { setAuthToken } from "./lib/api";
import Search from "./components/Search.jsx";

const initialAuth = {
  token: localStorage.getItem("ukb_token"),
  role: localStorage.getItem("ukb_role")
};

export default function App() {
  const [auth, setAuth] = useState(initialAuth);
  const [error, setError] = useState("");

  useEffect(() => {
    setAuthToken(auth.token);
  }, [auth.token]);

  const isAuthenticated = useMemo(() => Boolean(auth.token), [auth.token]);

  const handleLogin = async (event) => {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      const response = await api.post("/auth/login", payload);
      const nextAuth = {
        token: response.data.access_token,
        role: response.data.role
      };
      setAuth(nextAuth);
      localStorage.setItem("ukb_token", nextAuth.token);
      localStorage.setItem("ukb_role", nextAuth.role);
    } catch (err) {
      setError("Login failed. Please check your credentials.");
    }
  };

  const handleLogout = () => {
    setAuth({ token: null, role: null });
    localStorage.removeItem("ukb_token");
    localStorage.removeItem("ukb_role");
    setAuthToken(null);
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100">
        <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/80 p-8 shadow-xl">
          <div className="flex items-center gap-3 text-union-200">
            <Shield className="h-8 w-8" />
            <h1 className="text-2xl font-semibold">Union Knowledge Base</h1>
          </div>
          <p className="mt-2 text-sm text-slate-400">
            Secure access for stewards and administrators.
          </p>
          <form onSubmit={handleLogin} className="mt-6 space-y-4">
            <label className="block">
              <span className="text-sm text-slate-300">Username</span>
              <input
                name="username"
                required
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-slate-100 focus:border-union-400 focus:outline-none"
              />
            </label>
            <label className="block">
              <span className="text-sm text-slate-300">Password</span>
              <input
                name="password"
                type="password"
                required
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-slate-100 focus:border-union-400 focus:outline-none"
              />
            </label>
            {error ? <p className="text-sm text-red-400">{error}</p> : null}
            <button
              type="submit"
              className="w-full rounded-lg bg-union-500 px-4 py-2 text-sm font-semibold text-white hover:bg-union-400"
            >
              Sign in
            </button>
          </form>
          <div className="mt-6 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Local-only authentication
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Search role={auth.role} onLogout={handleLogout} />
    </div>
  );
}
