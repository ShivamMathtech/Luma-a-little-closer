import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Download, Mail, LogOut, Shield, Camera } from "lucide-react";
import { api, mutate, upload } from "../../lib/api";
import { queryClient, useAction } from "../../lib/query";
import {
  Avatar,
  Person,
  ErrorNote,
  Confirm,
  Modal,
  useToast,
} from "../../components/ui";
import { useMe } from "../auth/Auth";
import type { User } from "../../types/api";
export default function Settings() {
  const me = useMe();
  const toast = useToast();
  const navigate = useNavigate();
  const [name, setName] = useState(me.display_name);
  const [bio, setBio] = useState(me.bio);
  const [website, setWebsite] = useState(me.website);
  const [privateAccount, setPrivateAccount] = useState(me.is_private);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [logoutAll, setLogoutAll] = useState(false);
  const [localError, setLocalError] = useState<unknown>();
  const [avatarBusy, setAvatarBusy] = useState(false);
  const relations = useQuery({
    queryKey: ["relationships"],
    queryFn: async () => ({
      blocks: await api<{ items: User[] }>("/users/me/relationships/blocks"),
      mutes: await api<{ items: User[] }>("/users/me/relationships/mutes"),
    }),
  });
  const action = useAction(
    ({
      path,
      method,
      data,
    }: {
      path: string;
      method: string;
      data?: unknown;
    }) => mutate(path, method, data),
  );
  async function avatar(file?: File) {
    if (!file) return;
    setAvatarBusy(true);
    setLocalError(undefined);
    try {
      const a = await upload(file, () => undefined);
      await mutate("/users/me", "PATCH", { avatar_id: a.id });
      await queryClient.invalidateQueries();
      toast("Profile photo updated");
    } catch (e) {
      setLocalError(e);
    } finally {
      setAvatarBusy(false);
    }
  }
  async function exportData() {
    try {
      const data = await api("/users/me/export");
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "luma-account-export.json";
      a.click();
      URL.revokeObjectURL(url);
      toast("Account export downloaded");
    } catch (e) {
      setLocalError(e);
    }
  }
  function signedOut() {
    queryClient.clear();
    navigate("/login");
  }
  return (
    <main className="settings-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">MAKE YOURSELF COMFORTABLE</span>
          <h1>Your space. Your settings.</h1>
        </div>
      </header>
      <ErrorNote error={localError || action.error} />
      <section className="panel">
        <h2>Your profile</h2>
        <div className="avatar-editor">
          <Avatar user={me} size={72} />
          <label className="button secondary small">
            <Camera size={16} />
            {avatarBusy ? "Uploading…" : "Change photo"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={avatarBusy}
              onChange={(e) => avatar(e.target.files?.[0])}
            />
          </label>
          {me.avatar_id && (
            <button
              className="subtle-link"
              disabled={action.isPending}
              onClick={() =>
                action.mutate({
                  path: "/users/me",
                  method: "PATCH",
                  data: { avatar_id: null },
                })
              }
            >
              Remove
            </button>
          )}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            action.mutate(
              {
                path: "/users/me",
                method: "PATCH",
                data: { display_name: name, bio, website },
              },
              { onSuccess: () => toast("Profile updated") },
            );
          }}
        >
          <label>
            Display name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={80}
            />
          </label>
          <label>
            Bio
            <textarea
              rows={3}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              maxLength={300}
              placeholder="A little about your world…"
            />
          </label>
          <label>
            Website
            <input
              type="url"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="https://"
              maxLength={300}
            />
          </label>
          <button className="button" disabled={action.isPending}>
            Save profile
          </button>
        </form>
      </section>
      <section className="panel">
        <h2>
          <Shield size={21} /> Privacy & security
        </h2>
        <div className="setting-row">
          <div>
            <strong>Private account</strong>
            <p>Only approved followers can see your posts and stories.</p>
          </div>
          <input
            aria-label="Private account"
            type="checkbox"
            className="switch"
            checked={privateAccount}
            disabled={action.isPending}
            onChange={(e) => {
              const value = e.target.checked;
              action.mutate(
                {
                  path: "/users/me",
                  method: "PATCH",
                  data: { is_private: value },
                },
                {
                  onSuccess: () => {
                    setPrivateAccount(value);
                    toast(
                      value
                        ? "Your account is now private"
                        : "Your account is now public",
                    );
                  },
                },
              );
            }}
          />
        </div>
        <div className="setting-row">
          <div>
            <strong>Email address</strong>
            <p>
              {me.email} · {me.is_verified ? "Verified" : "Not yet verified"}
            </p>
          </div>
          {!me.is_verified && (
            <button
              className="button secondary small"
              disabled={action.isPending}
              onClick={() =>
                action.mutate(
                  { path: "/auth/resend-verification", method: "POST" },
                  { onSuccess: () => toast("Verification email queued") },
                )
              }
            >
              <Mail size={15} /> Verify
            </button>
          )}
        </div>
        {!me.is_verified && (
          <p className="info-note">
            For local development, run the worker and open the verification
            email in backend/var/mail.
          </p>
        )}
        <div className="button-row">
          <button
            className="button secondary small"
            disabled={action.isPending}
            onClick={() =>
              action.mutate(
                {
                  path: "/auth/forgot-password",
                  method: "POST",
                  data: { email: me.email },
                },
                { onSuccess: () => toast("Password reset email queued") },
              )
            }
          >
            Reset password
          </button>
          <button
            className="button secondary small"
            onClick={() => setLogoutAll(true)}
          >
            <LogOut size={15} /> Sign out everywhere
          </button>
        </div>
      </section>
      <section className="panel">
        <h2>Quiet your corner</h2>
        <ErrorNote error={relations.error} />
        {(["blocks", "mutes"] as const).map((kind) => (
          <div key={kind}>
            <h3>{kind === "blocks" ? "Blocked accounts" : "Muted accounts"}</h3>
            {relations.data?.[kind].items.map((u) => (
              <Person user={u} key={u.id}>
                <button
                  className="button secondary small"
                  disabled={action.isPending}
                  onClick={() =>
                    action.mutate({
                      path: `/users/${u.id}/${kind === "blocks" ? "block" : "mute"}`,
                      method: "DELETE",
                    })
                  }
                >
                  {kind === "blocks" ? "Unblock" : "Unmute"}
                </button>
              </Person>
            ))}
            {relations.data?.[kind].items.length === 0 && (
              <p className="muted">
                No {kind === "blocks" ? "blocked" : "muted"} accounts.
              </p>
            )}
          </div>
        ))}
      </section>
      <section className="panel">
        <h2>Your data</h2>
        <p className="muted">
          Download your account information, posts, comments, and messages you
          sent as JSON. Media identifiers are included; the export does not
          contain media files.
        </p>
        <button className="button secondary" onClick={exportData}>
          <Download size={17} /> Export account data
        </button>
        <div className="danger-zone">
          <h3>Delete account</h3>
          <p>
            Your account and associated content will be removed. This action
            cannot be undone.
          </p>
          <button
            className="button danger small"
            onClick={() => setDeleteOpen(true)}
          >
            Delete my account
          </button>
        </div>
      </section>
      {logoutAll && (
        <Confirm
          title="Sign out everywhere?"
          message="This will revoke every active session, including this one."
          onClose={() => setLogoutAll(false)}
          busy={action.isPending}
          error={action.error}
          action={() =>
            action.mutate(
              { path: "/auth/logout-all", method: "POST" },
              { onSuccess: signedOut },
            )
          }
        />
      )}{" "}
      {deleteOpen && (
        <Modal
          title="Permanently delete your account?"
          onClose={() => setDeleteOpen(false)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action.mutate(
                { path: "/users/me", method: "DELETE", data: { password } },
                { onSuccess: signedOut },
              );
            }}
          >
            <p>Enter your password to confirm permanent deletion.</p>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <ErrorNote error={action.error} />
            <button className="button danger" disabled={action.isPending}>
              Permanently delete
            </button>
          </form>
        </Modal>
      )}
    </main>
  );
}
