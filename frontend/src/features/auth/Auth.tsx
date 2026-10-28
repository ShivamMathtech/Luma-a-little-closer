import { createContext, useContext } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Navigate,
  Outlet,
  Link,
  useNavigate,
  useLocation,
  useSearchParams,
} from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { ArrowRight, Aperture } from "lucide-react";
import { api, ApiError, mutate } from "../../lib/api";
import { queryClient } from "../../lib/query";
import { Brand, Spinner, ErrorNote } from "../../components/ui";
import type { Me } from "../../types/api";
const AuthContext = createContext<Me | null>(null);
export function useMe() {
  const user = useContext(AuthContext);
  if (!user) throw new Error("Authentication context missing");
  return user;
}
export function Protected() {
  const q = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("/auth/me"),
    retry: false,
    refetchInterval: 60000,
  });
  const location = useLocation();
  if (q.isPending) return <Spinner />;
  if (q.error instanceof ApiError && q.error.status === 401)
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (q.error)
    return (
      <main className="standalone">
        <ErrorNote error={q.error} retry={() => q.refetch()} />
      </main>
    );
  if (!q.data) return null;
  return (
    <AuthContext.Provider value={q.data}>
      <Outlet />
    </AuthContext.Provider>
  );
}
const loginSchema = z.object({
  login: z.string().min(1, "Enter your username or email"),
  password: z.string().min(1, "Enter your password"),
});
const registerSchema = z.object({
  username: z
    .string()
    .min(3)
    .max(30)
    .regex(/^[a-zA-Z0-9_]+$/, "Use letters, numbers and underscores"),
  display_name: z.string().min(1).max(80),
  email: z.email(),
  password: z
    .string()
    .min(12, "Use at least 12 characters")
    .max(128)
    .regex(/[0-9]/, "Include a number")
    .regex(/[a-zA-Z]/, "Include a letter"),
});
type AuthFields = {
  login?: string;
  username?: string;
  display_name?: string;
  email?: string;
  password: string;
};
export function AuthPage({ register = false }: { register?: boolean }) {
  const [error, setError] = useState<unknown>();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    register: field,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AuthFields>({
    resolver: zodResolver(register ? registerSchema : loginSchema) as never,
  });
  async function submit(values: AuthFields) {
    setError(undefined);
    try {
      const user = await mutate<Me>(
        register ? "/auth/register" : "/auth/login",
        "POST",
        values,
      );
      queryClient.clear();
      queryClient.setQueryData(["me"], user);
      const from = location.state?.from;
      navigate(
        typeof from === "string" &&
          from.startsWith("/") &&
          !from.startsWith("//")
          ? from
          : "/home",
      );
    } catch (e) {
      setError(e);
    }
  }
  const fields: {
    name: keyof AuthFields;
    label: string;
    type: string;
    complete: string;
  }[] = register
    ? [
        {
          name: "display_name",
          label: "Your name",
          type: "text",
          complete: "name",
        },
        {
          name: "username",
          label: "Username",
          type: "text",
          complete: "username",
        },
        {
          name: "email",
          label: "Email address",
          type: "email",
          complete: "email",
        },
        {
          name: "password",
          label: "Password",
          type: "password",
          complete: "new-password",
        },
      ]
    : [
        {
          name: "login",
          label: "Username or email",
          type: "text",
          complete: "username",
        },
        {
          name: "password",
          label: "Password",
          type: "password",
          complete: "current-password",
        },
      ];
  return (
    <div className="auth-page">
      <div className="auth-art">
        <Brand />
        <div>
          <span className="eyebrow">MADE FOR YOUR EVERYDAY</span>
          <h1>
            Good things
            <br />
            are better
            <br />
            <em>shared.</em>
          </h1>
          <p>Your moments. Your people. A little closer.</p>
          <div className="auth-orbit">
            <Aperture size={150} strokeWidth={0.7} />
          </div>
        </div>
        <small>AN ORIGINAL PLACE TO CONNECT.</small>
      </div>
      <main className="auth-form">
        <Brand />
        <span className="eyebrow">
          {register ? "MAKE YOURSELF AT HOME" : "YOUR PEOPLE ARE HERE"}
        </span>
        <h1>{register ? "A fresh perspective." : "Welcome back."}</h1>
        <p>
          {register
            ? "Start sharing the things that make you, you."
            : "Pick up where you left off."}
        </p>
        <form onSubmit={handleSubmit(submit)} noValidate>
          {fields.map((f) => (
            <label key={f.name}>
              {f.label}
              <input
                type={f.type}
                autoComplete={f.complete}
                {...field(f.name)}
                aria-invalid={!!errors[f.name]}
              />
              {errors[f.name] && (
                <small className="field-error">{errors[f.name]?.message}</small>
              )}
            </label>
          ))}
          {register && (
            <small className="muted">
              Use at least 12 characters with a letter and a number.
            </small>
          )}
          <ErrorNote error={error} />
          <button className="button wide" disabled={isSubmitting}>
            {isSubmitting
              ? "Please wait…"
              : register
                ? "Create your account"
                : "Sign in"}
            <ArrowRight size={18} />
          </button>
        </form>
        {!register && <Link to="/forgot-password">Forgot your password?</Link>}
        <p className="auth-switch">
          {register ? "Already part of Luma?" : "New around here?"}{" "}
          <Link to={register ? "/login" : "/signup"}>
            {register ? "Sign in" : "Join Luma"}
          </Link>
        </p>
      </main>
    </div>
  );
}
export function RecoveryPage({
  mode,
}: {
  mode: "forgot-password" | "reset-password" | "verify-email";
}) {
  const [params] = useSearchParams();
  const [error, setError] = useState<unknown>();
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    const values = new FormData(e.currentTarget);
    try {
      await mutate(
        `/auth/${mode}`,
        "POST",
        mode === "forgot-password"
          ? { email: values.get("email") }
          : mode === "reset-password"
            ? { token: params.get("token"), password: values.get("password") }
            : { token: params.get("token") },
      );
      setDone(true);
      queryClient.invalidateQueries({ queryKey: ["me"] });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="standalone recovery">
      <Brand />
      <div className="panel">
        <h1>
          {mode === "forgot-password"
            ? "Let’s get you back in."
            : mode === "reset-password"
              ? "Choose a new password."
              : "Verify your email."}
        </h1>
        {done ? (
          <>
            <p>
              {mode === "forgot-password"
                ? "If an account exists, a recovery email will arrive shortly. In local development, run the worker and open backend/var/mail."
                : "All done. You can return to Luma."}
            </p>
            <Link className="button" to="/login">
              Continue to sign in
            </Link>
          </>
        ) : (
          <form onSubmit={submit}>
            {mode === "forgot-password" && (
              <label>
                Email address
                <input
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                />
              </label>
            )}
            {mode === "reset-password" && (
              <label>
                New password
                <input
                  name="password"
                  type="password"
                  minLength={12}
                  maxLength={128}
                  required
                  autoComplete="new-password"
                />
                <small>12+ characters, including a letter and a number.</small>
              </label>
            )}
            <ErrorNote error={error} />
            <button
              className="button"
              disabled={
                busy || (mode !== "forgot-password" && !params.get("token"))
              }
            >
              {busy
                ? "Working…"
                : mode === "forgot-password"
                  ? "Send recovery email"
                  : "Confirm"}
            </button>
            {mode !== "forgot-password" && !params.get("token") && (
              <p className="muted">Open the full link from your email.</p>
            )}
          </form>
        )}
      </div>
    </main>
  );
}
