import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MediaView } from "../../components/Social";
import { Link } from "react-router-dom";
import { usePages, useAction } from "../../lib/query";
import { api, mutate } from "../../lib/api";
import { useMe } from "../auth/Auth";
import type { Report, Post, User } from "../../types/api";
import {
  ErrorNote,
  Spinner,
  Empty,
  Modal,
  LoadMore,
  dateLabel,
  useToast,
} from "../../components/ui";
export default function Admin() {
  const me = useMe();
  const [status, setStatus] = useState("open");
  const [selected, setSelected] = useState<Report | null>(null);
  const [decision, setDecision] = useState("dismiss");
  const [note, setNote] = useState("");
  const toast = useToast();
  const q = usePages<Report>(
    "/admin/reports?status=" + status,
    me.role === "admin",
  );
  const content = useQuery({
    queryKey: ["report-content", selected?.id],
    queryFn: () =>
      api<{
        available: boolean;
        message?: string;
        post?: Post;
        body?: string;
        author?: User;
      }>(`/admin/reports/${selected?.id}/content`),
    enabled: !!selected,
  });
  const action = useAction(() =>
    mutate(`/admin/reports/${selected?.id}/actions`, "POST", {
      action: decision,
      note,
    }),
  );
  if (me.role !== "admin")
    return (
      <Empty
        title="Administrator access required."
        text="This area is available to moderators only."
      />
    );
  return (
    <main className="wide-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">CARE FOR THE COMMUNITY</span>
          <h1>Moderation queue.</h1>
          <p>
            Review thoughtfully. Every action is recorded in the audit trail.
          </p>
        </div>
        <label>
          Show
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="open">Open reports</option>
            <option value="all">All reports</option>
          </select>
        </label>
      </header>
      <ErrorNote error={q.error} />
      {q.isPending && <Spinner />}
      <div className="report-list">
        {q.data?.pages
          .flatMap((p) => p.items)
          .map((r) => (
            <article className="panel" key={r.id}>
              <div className="section-heading">
                <strong>{r.target_type.toUpperCase()} REPORT</strong>
                <span className="chip">{r.status}</span>
              </div>
              <p>{r.reason}</p>
              <small className="muted">
                {dateLabel(r.created_at)} · {r.target_id}
              </small>
              <div className="button-row">
                {r.target_type === "post" && (
                  <Link
                    className="button secondary small"
                    to={`/p/${r.target_id}`}
                  >
                    View post
                  </Link>
                )}
                {r.status === "open" && (
                  <button
                    className="button small"
                    onClick={() => {
                      setSelected(r);
                      setDecision("dismiss");
                      setNote("");
                    }}
                  >
                    Review report
                  </button>
                )}
              </div>
            </article>
          ))}
      </div>
      {q.data?.pages[0].items.length === 0 && (
        <Empty
          title="The queue is clear."
          text="New reports from your community will appear here."
        />
      )}
      <LoadMore
        hasNext={q.hasNextPage}
        loading={q.isFetchingNextPage}
        load={() => q.fetchNextPage()}
      />
      {selected && (
        <Modal title="Resolve report" onClose={() => setSelected(null)}>
          <ErrorNote error={content.error} />
          {content.isPending && <Spinner />}
          {content.data?.post && (
            <div className="review-content">
              <p>
                <strong>@{content.data.post.author.username}</strong>{" "}
                {content.data.post.caption}
              </p>
              {content.data.post.media.map((a) => (
                <div className="review-media" key={a.id}>
                  <MediaView asset={a} />
                </div>
              ))}
            </div>
          )}
          {content.data?.author && (
            <p>
              <strong>@{content.data.author.username}</strong>{" "}
              {content.data.body || content.data.author.bio}
            </p>
          )}
          {content.data?.message && <p>{content.data.message}</p>}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action.mutate(undefined, {
                onSuccess: () => {
                  setSelected(null);
                  toast("Moderation action recorded");
                },
              });
            }}
          >
            <label>
              Action
              <select
                value={decision}
                onChange={(e) => setDecision(e.target.value)}
              >
                <option value="dismiss">Dismiss report</option>
                {selected.target_type !== "user" && (
                  <option value="remove">Remove content</option>
                )}
                <option value="suspend">Suspend account</option>
              </select>
            </label>
            <label>
              Review note
              <textarea
                rows={4}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                required
                minLength={3}
                maxLength={1000}
              />
            </label>
            <ErrorNote error={action.error} />
            <button className="button" disabled={action.isPending}>
              Confirm action
            </button>
          </form>
        </Modal>
      )}
    </main>
  );
}
