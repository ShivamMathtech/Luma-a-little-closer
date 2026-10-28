import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useId,
} from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Check, LoaderCircle, X, Aperture, ArrowRight } from "lucide-react";
import { mediaUrl } from "../lib/api";
import type { User } from "../types/api";
export function Brand() {
  return (
    <Link to="/" className="brand" aria-label="Luma home">
      <Aperture size={30} strokeWidth={2.2} />
      <span>luma</span>
      <i />
    </Link>
  );
}
export function Avatar({ user, size = 40 }: { user: User; size?: number }) {
  return (
    <span
      className="avatar"
      style={{
        width: size,
        height: size,
        minWidth: size,
        fontSize: size * 0.33,
      }}
    >
      {user.avatar_id ? (
        <img
          src={mediaUrl({ url: `/api/v1/media/${user.avatar_id}` })}
          alt=""
        />
      ) : (
        user.display_name.slice(0, 2).toUpperCase()
      )}
    </span>
  );
}
export function Person({
  user,
  children,
}: {
  user: User;
  children?: ReactNode;
}) {
  return (
    <div className="person">
      <Link to={`/u/${user.username}`}>
        <Avatar user={user} />
      </Link>
      <Link className="person-name" to={`/u/${user.username}`}>
        <strong>{user.display_name}</strong>
        <small>@{user.username}</small>
      </Link>
      {children}
    </div>
  );
}
export function Spinner() {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={23} />
      <span>Loading…</span>
    </div>
  );
}
export function ErrorNote({
  error,
  retry,
}: {
  error?: unknown;
  retry?: () => void;
}) {
  if (!error) return null;
  return (
    <div className="error-note" role="alert">
      {error instanceof Error ? error.message : String(error)}
      {retry && <button onClick={retry}>Try again</button>}
    </div>
  );
}
export function Empty({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <Aperture size={38} />
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}
export function LoadMore({
  hasNext,
  loading,
  load,
}: {
  hasNext?: boolean;
  loading: boolean;
  load: () => void;
}) {
  return hasNext ? (
    <button
      className="button secondary load-more"
      disabled={loading}
      onClick={load}
    >
      {loading ? "Loading…" : "Load more"}
      <ArrowRight size={16} />
    </button>
  ) : null;
}
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const titleId = useId();
  const ref = useRef<HTMLDialogElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    d.showModal();
    const handler = (e: Event) => {
      e.preventDefault();
      close.current();
    };
    d.addEventListener("cancel", handler);
    return () => {
      d.removeEventListener("cancel", handler);
      d.close();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={titleId}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="modal-header">
        <h2 id={titleId}>{title}</h2>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close dialog"
        >
          <X />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Confirm({
  title,
  message,
  onClose,
  action,
  busy,
  error,
}: {
  title: string;
  message: string;
  onClose: () => void;
  action: () => void;
  busy?: boolean;
  error?: unknown;
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <p>{message}</p>
      <ErrorNote error={error} />
      <div className="button-row">
        <button className="button secondary" onClick={onClose}>
          Cancel
        </button>
        <button className="button danger" onClick={action} disabled={busy}>
          {busy ? "Working…" : "Confirm"}
        </button>
      </div>
    </Modal>
  );
}
const ToastContext = createContext<(message: string) => void>(() => undefined);
export const useToast = () => useContext(ToastContext);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (message) {
      const t = setTimeout(() => setMessage(""), 4000);
      return () => clearTimeout(t);
    }
  }, [message]);
  return (
    <ToastContext.Provider value={setMessage}>
      {children}
      {message && (
        <div className="toast" role="status">
          <Check size={18} />
          {message}
          <button onClick={() => setMessage("")} aria-label="Dismiss">
            <X size={16} />
          </button>
        </div>
      )}
    </ToastContext.Provider>
  );
}
export const dateLabel = (value: string) =>
  new Date(
    value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value) ? value : value + "Z",
  ).toLocaleDateString(undefined, { month: "short", day: "numeric" });
