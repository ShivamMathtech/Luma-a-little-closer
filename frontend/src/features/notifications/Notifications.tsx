import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CheckCheck } from "lucide-react";
import { api, mutate } from "../../lib/api";
import { usePages, useAction } from "../../lib/query";
import type { Notice, User, Page } from "../../types/api";
import {
  Avatar,
  Spinner,
  ErrorNote,
  Empty,
  LoadMore,
  Person,
  dateLabel,
} from "../../components/ui";
const labels: Record<string, string> = {
  like: "liked your moment",
  comment: "commented on your moment",
  reply: "replied to your comment",
  mention: "mentioned you in a moment",
  follow: "started following you",
  follow_request: "sent you a follow request",
  follow_accepted: "accepted your follow request",
  message: "sent you a message",
};
export default function Notifications() {
  const q = usePages<Notice>("/notifications");
  const requests = useQuery({
    queryKey: ["follow-requests"],
    queryFn: () =>
      api<Page<{ id: string; user: User }>>("/users/me/follow-requests"),
  });
  const action = useAction(
    ({ path, method }: { path: string; method: string }) =>
      mutate(path, method),
  );
  return (
    <main className="narrow-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">GOOD THINGS COME AROUND</span>
          <h1>Your little updates.</h1>
        </div>
        <button
          className="button secondary small"
          disabled={action.isPending}
          onClick={() =>
            action.mutate({ path: "/notifications/read-all", method: "POST" })
          }
        >
          <CheckCheck size={16} /> Read all
        </button>
      </header>
      <ErrorNote error={q.error || requests.error || action.error} />
      {requests.data?.items.length ? (
        <section className="panel requests">
          <h3>Follow requests</h3>
          {requests.data.items.map((r) => (
            <Person key={r.id} user={r.user}>
              <div className="button-row">
                <button
                  className="button small"
                  disabled={action.isPending}
                  onClick={() =>
                    action.mutate({
                      path: `/users/me/follow-requests/${r.id}/accept`,
                      method: "POST",
                    })
                  }
                >
                  Accept
                </button>
                <button
                  className="button secondary small"
                  disabled={action.isPending}
                  onClick={() =>
                    action.mutate({
                      path: `/users/me/follow-requests/${r.id}`,
                      method: "DELETE",
                    })
                  }
                >
                  Decline
                </button>
              </div>
            </Person>
          ))}
        </section>
      ) : null}
      {q.isPending && <Spinner />}
      <div className="notice-list">
        {q.data?.pages
          .flatMap((p) => p.items)
          .map((n) => (
            <div className={`notice ${!n.is_read ? "unread" : ""}`} key={n.id}>
              <Avatar user={n.actor} />
              <div>
                <Link
                  to={
                    ["like", "comment", "reply", "mention"].includes(n.kind)
                      ? `/p/${n.target_id}`
                      : n.kind === "message"
                        ? `/messages/${n.target_id}`
                        : `/u/${n.actor.username}`
                  }
                >
                  <strong>{n.actor.username}</strong> {labels[n.kind] || n.kind}
                  .
                </Link>
                <small>{dateLabel(n.created_at)}</small>
              </div>
              <button
                className="read-dot"
                aria-label={n.is_read ? "Mark unread" : "Mark read"}
                disabled={action.isPending}
                onClick={() =>
                  action.mutate({
                    path: `/notifications/${n.id}?is_read=${!n.is_read}`,
                    method: "PATCH",
                  })
                }
              >
                {n.is_read ? "○" : "●"}
              </button>
            </div>
          ))}
      </div>
      {q.data?.pages[0].items.length === 0 && (
        <Empty
          title="All quiet for now."
          text="Your follows, conversations, and little appreciations will appear here."
        />
      )}
      <LoadMore
        hasNext={q.hasNextPage}
        loading={q.isFetchingNextPage}
        load={() => q.fetchNextPage()}
      />
    </main>
  );
}
