import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { NavLink, Link, Outlet, useNavigate } from "react-router-dom";
import {
  Home,
  Compass,
  Clapperboard,
  MessageCircle,
  Heart,
  Bookmark,
  Plus,
  Settings,
  Moon,
  Sun,
  LogOut,
  Shield,
  MoreHorizontal,
} from "lucide-react";
import type { Notice, Page, Conversation } from "../types/api";
import { api, mutate } from "../lib/api";
import { queryClient } from "../lib/query";
import { useMe } from "../features/auth/Auth";
import { Brand, Avatar, ErrorNote } from "../components/ui";
const links = [
  { to: "/home", label: "Home", icon: Home },
  { to: "/explore", label: "Explore", icon: Compass },
  { to: "/reels", label: "Reels", icon: Clapperboard },
  { to: "/messages", label: "Messages", icon: MessageCircle },
  { to: "/notifications", label: "Notifications", icon: Heart },
  { to: "/saved", label: "Saved", icon: Bookmark },
];
export default function Shell() {
  const me = useMe();
  const navigate = useNavigate();
  const [dark, setDark] = useState(
    () => localStorage.getItem("luma-theme") === "dark",
  );
  const [mobileMenu, setMobileMenu] = useState(false);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const notices = useQuery({
    queryKey: ["notice-count"],
    queryFn: () =>
      api<Page<Notice> & { unread_count: number }>("/notifications?limit=1"),
    refetchInterval: 15000,
  });
  const chats = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api<Page<Conversation>>("/conversations?limit=50"),
    refetchInterval: 10000,
  });
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("luma-theme", dark ? "dark" : "light");
  }, [dark]);
  async function logout() {
    setBusy(true);
    try {
      await mutate("/auth/logout");
      queryClient.clear();
      navigate("/login");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  const unreadMessages =
    chats.data?.items.reduce((n, c) => n + c.unread_count, 0) || 0;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#content">
        Skip to content
      </a>
      <aside className="app-sidebar">
        <Brand />
        <span className="sidebar-tagline">A little closer.</span>
        <nav aria-label="Main navigation">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink to={to} key={to}>
              <Icon size={22} />
              <span>{label}</span>
              {(
                to === "/notifications"
                  ? notices.data?.unread_count
                  : to === "/messages"
                    ? unreadMessages
                    : 0
              ) ? (
                <i className="nav-dot" />
              ) : null}
            </NavLink>
          ))}
          <NavLink to={`/u/${me.username}`}>
            <Avatar user={me} size={23} />
            <span>Profile</span>
          </NavLink>
        </nav>
        <Link className="button sidebar-create" to="/create">
          <Plus size={20} /> Create a moment
        </Link>
        <div className="sidebar-bottom">
          {me.role === "admin" && (
            <NavLink to="/admin">
              <Shield size={19} /> Moderation
            </NavLink>
          )}
          <NavLink to="/settings">
            <Settings size={19} /> Settings
          </NavLink>
          <button onClick={() => setDark(!dark)}>
            {dark ? <Sun size={19} /> : <Moon size={19} />}{" "}
            {dark ? "Light mode" : "Dark mode"}
          </button>
          <button onClick={logout} disabled={busy}>
            <LogOut size={19} /> {busy ? "Signing out…" : "Sign out"}
          </button>
          <ErrorNote error={error} />
          <div className="signed-in">
            <Avatar user={me} size={34} />
            <div>
              <strong>{me.display_name}</strong>
              <small>@{me.username}</small>
            </div>
            <span className="live-dot" />
          </div>
        </div>
      </aside>
      <header className="mobile-header">
        <Brand />
        <div>
          <button
            className="icon-button"
            aria-label="Switch theme"
            onClick={() => setDark(!dark)}
          >
            {dark ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <Link
            to="/notifications"
            className="icon-button"
            aria-label="Notifications"
          >
            <Heart size={20} />
          </Link>
          <Link to="/settings" className="icon-button" aria-label="Settings">
            <Settings size={20} />
          </Link>
          <div className="menu-wrap">
            <button
              className="icon-button"
              aria-label="More navigation"
              aria-expanded={mobileMenu}
              onClick={() => setMobileMenu(!mobileMenu)}
            >
              <MoreHorizontal size={20} />
            </button>
            {mobileMenu && (
              <div className="dropdown">
                <Link to="/reels" onClick={() => setMobileMenu(false)}>
                  Reels
                </Link>
                <Link to="/saved" onClick={() => setMobileMenu(false)}>
                  Saved
                </Link>
                {me.role === "admin" && (
                  <Link to="/admin" onClick={() => setMobileMenu(false)}>
                    Moderation
                  </Link>
                )}
                <button onClick={logout} disabled={busy}>
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>
      <div className="app-content" id="content">
        <Outlet />
      </div>
      <nav className="mobile-navigation" aria-label="Mobile navigation">
        <NavLink to="/home" aria-label="Home">
          <Home />
        </NavLink>
        <NavLink to="/explore" aria-label="Explore">
          <Compass />
        </NavLink>
        <NavLink to="/create" className="mobile-create" aria-label="Create">
          <Plus />
        </NavLink>
        <NavLink to="/messages" aria-label="Messages">
          <MessageCircle />
        </NavLink>
        <NavLink to={`/u/${me.username}`} aria-label="Profile">
          <Avatar user={me} size={25} />
        </NavLink>
      </nav>
    </div>
  );
}
