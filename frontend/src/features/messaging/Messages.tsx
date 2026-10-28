import { useState, useEffect, useRef } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus, Send, Paperclip, X, ArrowLeft } from "lucide-react";
import { api, mutate, upload } from "../../lib/api";
import { useAction } from "../../lib/query";
import type {
  Conversation,
  Page,
  SearchResult,
  History,
  Asset,
} from "../../types/api";
import {
  Avatar,
  Modal,
  Person,
  Spinner,
  ErrorNote,
  Empty,
  useToast,
  dateLabel,
} from "../../components/ui";
import { MediaView } from "../../components/Social";
import { useMe } from "../auth/Auth";
export default function Messages() {
  const me = useMe();
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [newChat, setNewChat] = useState(false);
  const [search, setSearch] = useState("");
  const [term, setTerm] = useState("");
  const [body, setBody] = useState("");
  const [older, setOlder] = useState<History["items"]>([]);
  const [oldCursor, setOldCursor] = useState<string | null | undefined>();
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<unknown>();
  const [attachment, setAttachment] = useState<Asset | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<unknown>();
  const [progress, setProgress] = useState(0);
  const clientId = useRef(crypto.randomUUID());
  const chats = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api<Page<Conversation>>("/conversations?limit=50"),
    refetchInterval: 5000,
  });
  const history = useQuery({
    queryKey: ["messages", id],
    queryFn: () => api<History>(`/conversations/${id}/messages`),
    enabled: !!id,
    refetchInterval: 3000,
  });
  const [extraChats, setExtraChats] = useState<Conversation[]>([]);
  const [chatCursor, setChatCursor] = useState<string | null | undefined>();
  const [chatBusy, setChatBusy] = useState(false);
  const searchQ = useQuery({
    queryKey: ["chat-search", term],
    queryFn: () => api<SearchResult>("/search?q=" + encodeURIComponent(term)),
    enabled: newChat && term.length >= 2,
  });
  const create = useAction((userId: string) =>
    mutate<{ id: string }>("/conversations", "POST", { user_id: userId }),
  );
  const send = useAction(() =>
    mutate(`/conversations/${id}/messages`, "POST", {
      body,
      client_id: clientId.current,
      media_ids: attachment ? [attachment.id] : [],
    }),
  );
  const mark = useAction((cid: string) => mutate(`/conversations/${cid}/read`));
  const newest = history.data?.items[0]?.id;
  useEffect(() => {
    const t = setTimeout(() => setTerm(search), 300);
    return () => clearTimeout(t);
  }, [search]);
  useEffect(() => {
    setOlder([]);
    setOldCursor(undefined);
    setBody("");
    setAttachment(null);
    setHistoryError(undefined);
    clientId.current = crypto.randomUUID();
  }, [id]);
  useEffect(() => {
    if (id && newest) mark.mutate(id);
  }, [id, newest]);
  const members = history.data?.members || [];
  const other = members.find((m) => m.user.id !== me.id);
  const messages = [
    ...new Map(
      [...(history.data?.items || []), ...older].map((m) => [m.id, m]),
    ).values(),
  ].sort(
    (a, b) =>
      a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id),
  );
  const availableCursor =
    oldCursor === undefined ? history.data?.next_cursor : oldCursor;
  async function loadOlder() {
    if (!availableCursor) return;
    setHistoryLoading(true);
    try {
      const p = await api<History>(
        `/conversations/${id}/messages?cursor=${encodeURIComponent(availableCursor)}`,
      );
      setOlder([...older, ...p.items]);
      setOldCursor(p.next_cursor);
    } catch (e) {
      setHistoryError(e);
    } finally {
      setHistoryLoading(false);
    }
  }
  async function attach(file?: File) {
    if (!file) return;
    setUploading(true);
    setUploadError(undefined);
    try {
      setAttachment(await upload(file, setProgress));
    } catch (e) {
      setUploadError(e);
    } finally {
      setUploading(false);
    }
  }
  async function moreChats() {
    const cursor =
      chatCursor === undefined ? chats.data?.next_cursor : chatCursor;
    if (!cursor) return;
    setChatBusy(true);
    try {
      const p = await api<Page<Conversation>>(
        "/conversations?cursor=" + encodeURIComponent(cursor),
      );
      setExtraChats([...extraChats, ...p.items]);
      setChatCursor(p.next_cursor);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not load conversations");
    } finally {
      setChatBusy(false);
    }
  }
  return (
    <main className={`messages-page ${id ? "has-thread" : ""}`}>
      <aside className="conversation-list">
        <div className="section-heading">
          <div>
            <span className="eyebrow">KEEP IN TOUCH</span>
            <h1>Messages.</h1>
          </div>
          <button
            className="icon-button"
            aria-label="New conversation"
            onClick={() => setNewChat(true)}
          >
            <Plus />
          </button>
        </div>
        <ErrorNote error={chats.error} />
        {chats.isPending && <Spinner />}
        {[
          ...new Map(
            [...(chats.data?.items || []), ...extraChats].map((c) => [c.id, c]),
          ).values(),
        ].map((c) => {
          const person = c.members.find((u) => u.id !== me.id);
          return (
            person && (
              <Link
                key={c.id}
                className={`conversation ${id === c.id ? "active" : ""}`}
                to={`/messages/${c.id}`}
              >
                <Avatar user={person} />
                <div>
                  <strong>{person.display_name}</strong>
                  <p>
                    {c.last_message?.body ||
                      (c.last_message ? "Shared an attachment" : "Say hello")}
                  </p>
                </div>
                {c.unread_count > 0 && (
                  <span className="badge">{c.unread_count}</span>
                )}
              </Link>
            )
          );
        })}
        {(chatCursor === undefined ? chats.data?.next_cursor : chatCursor) && (
          <button
            className="subtle-link"
            disabled={chatBusy}
            onClick={moreChats}
          >
            More conversations
          </button>
        )}
        {chats.data?.items.length === 0 && (
          <p className="muted padded">
            A simple hello can be the start of something.
          </p>
        )}
      </aside>
      <section className="message-thread">
        {!id ? (
          <Empty
            title="A little conversation goes a long way."
            text="Choose a conversation, or start a new one."
            action={
              <button className="button" onClick={() => setNewChat(true)}>
                Say hello <Plus size={16} />
              </button>
            }
          />
        ) : (
          <>
            <header className="thread-heading">
              <Link
                to="/messages"
                className="mobile-back icon-button"
                aria-label="Back to conversations"
              >
                <ArrowLeft />
              </Link>
              {other && <Person user={other.user} />}
              <span className="muted">Updates every 3s</span>
            </header>
            <div className="message-history">
              <ErrorNote error={history.error || historyError || mark.error} />
              {history.isPending && <Spinner />}
              {availableCursor && (
                <button
                  className="subtle-link"
                  disabled={historyLoading}
                  onClick={loadOlder}
                >
                  Load older messages
                </button>
              )}
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`message ${m.sender_id === me.id ? "mine" : ""}`}
                >
                  <div>
                    {m.body && <p>{m.body}</p>}
                    {m.attachments.map((a) => (
                      <div className="message-attachment" key={a.id}>
                        <MediaView asset={a} />
                      </div>
                    ))}
                  </div>
                  <small>
                    {dateLabel(m.created_at)} ·{" "}
                    {new Date(m.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                    {m.sender_id === me.id &&
                    other &&
                    new Date(other.last_read_at) >= new Date(m.created_at)
                      ? " · Seen"
                      : ""}
                  </small>
                </div>
              ))}
            </div>
            <div className="thread-compose">
              <ErrorNote error={send.error || uploadError} />
              {attachment && (
                <div className="attachment-chip">
                  Media attached{" "}
                  <button
                    className="icon-button"
                    aria-label="Remove attachment"
                    onClick={() => setAttachment(null)}
                  >
                    <X size={14} />
                  </button>
                </div>
              )}
              {uploading && <small>Uploading {progress}%</small>}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  send.mutate(undefined, {
                    onSuccess: () => {
                      setBody("");
                      setAttachment(null);
                      clientId.current = crypto.randomUUID();
                    },
                  });
                }}
              >
                <label
                  className="icon-button attachment-button"
                  aria-label="Attach media"
                >
                  <Paperclip size={20} />
                  <input
                    type="file"
                    aria-label="Attach media"
                    accept="image/jpeg,image/png,image/webp,video/mp4,video/webm"
                    disabled={uploading || send.isPending}
                    onChange={(e) => {
                      attach(e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                </label>
                <input
                  aria-label="Message"
                  placeholder="A little hello…"
                  value={body}
                  maxLength={3000}
                  onChange={(e) => setBody(e.target.value)}
                  disabled={send.isPending}
                />
                <button
                  className="button small"
                  aria-label="Send message"
                  disabled={
                    send.isPending || uploading || (!body.trim() && !attachment)
                  }
                >
                  <Send size={18} />
                </button>
              </form>
            </div>
          </>
        )}
      </section>
      {newChat && (
        <Modal title="Start a conversation" onClose={() => setNewChat(false)}>
          <label>
            Find someone
            <input
              autoFocus
              placeholder="Search username or name"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <ErrorNote error={searchQ.error || create.error} />
          {searchQ.isFetching && <Spinner />}
          {searchQ.data?.users.map((u) => (
            <Person key={u.id} user={u}>
              <button
                className="button small"
                disabled={create.isPending}
                onClick={() =>
                  create.mutate(u.id, {
                    onSuccess: (c) => {
                      setNewChat(false);
                      navigate(`/messages/${c.id}`);
                    },
                  })
                }
              >
                Chat
              </button>
            </Person>
          ))}
          <small className="muted">
            Private accounts must accept your follow request first.
          </small>
        </Modal>
      )}
    </main>
  );
}
