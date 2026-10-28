import { Component, lazy, Suspense } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "../lib/query";
import { ToastProvider, Spinner } from "../components/ui";
import { Protected, AuthPage, RecoveryPage } from "../features/auth/Auth";
import Shell from "./Shell";
import Landing from "../features/Landing";
import { Home, Explore, Reels, PostDetail } from "../features/feed/Feed";
const Create = lazy(() => import("../features/posts/Create"));
const Profile = lazy(() => import("../features/profiles/Profile"));
const Messages = lazy(() => import("../features/messaging/Messages"));
const Notifications = lazy(
  () => import("../features/notifications/Notifications"),
);
const Saved = lazy(() => import("../features/saved/Saved"));
const Settings = lazy(() => import("../features/settings/Settings"));
const Admin = lazy(() => import("../features/moderation/Admin"));
class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Luma UI error", error.name, info.componentStack);
  }
  render() {
    return this.state.error ? (
      <main className="standalone">
        <h1>Something interrupted the moment.</h1>
        <p>Reload the page to try again.</p>
        <button className="button" onClick={() => window.location.reload()}>
          Reload Luma
        </button>
      </main>
    ) : (
      this.props.children
    );
  }
}
export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <BrowserRouter>
            <Suspense fallback={<Spinner />}>
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<AuthPage />} />
                <Route path="/signup" element={<AuthPage register />} />
                <Route
                  path="/forgot-password"
                  element={<RecoveryPage mode="forgot-password" />}
                />
                <Route
                  path="/reset-password"
                  element={<RecoveryPage mode="reset-password" />}
                />
                <Route
                  path="/verify-email"
                  element={<RecoveryPage mode="verify-email" />}
                />
                <Route element={<Protected />}>
                  <Route element={<Shell />}>
                    <Route path="/home" element={<Home />} />
                    <Route path="/explore" element={<Explore />} />
                    <Route path="/reels" element={<Reels />} />
                    <Route path="/create" element={<Create />} />
                    <Route path="/p/:id" element={<PostDetail />} />
                    <Route path="/u/:username" element={<Profile />} />
                    <Route path="/messages" element={<Messages />} />
                    <Route path="/messages/:id" element={<Messages />} />
                    <Route path="/notifications" element={<Notifications />} />
                    <Route path="/saved" element={<Saved />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="/admin" element={<Admin />} />
                  </Route>
                </Route>
                <Route
                  path="*"
                  element={
                    <main className="standalone">
                      <h1>This page wandered off.</h1>
                      <Link to="/home" className="button">
                        Back to Luma
                      </Link>
                    </main>
                  }
                />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
