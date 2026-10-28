import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  Heart,
  MessageCircle,
  Bookmark,
  Send,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  Plus,
  Flag,
  Pencil,
  Trash2,
  FolderPlus,
} from "lucide-react";
import type {
  Asset,
  Post,
  Comment,
  User,
  Profile,
  Collection,
  Story,
  Page,
} from "../types/api";
import { api, mutate, mediaUrl } from "../lib/api";
import { usePages, useAction } from "../lib/query";
import { useMe } from "../features/auth/Auth";
import {
  Avatar,
  Person,
  Modal,
  ErrorNote,
  Confirm,
  Spinner,
  LoadMore,
  useToast,
  dateLabel,
} from "./ui";

export function MediaView({
  asset,
  autoplay = false,
  preview = false,
}: {
  asset: Asset;
  autoplay?: boolean;
  preview?: boolean;
}) {
  return asset.mime_type.startsWith("video/") ? (
    <video
      src={mediaUrl(asset)}
      controls={!preview}
      muted={autoplay || preview}
      autoPlay={autoplay}
      loop={autoplay}
      playsInline
      preload="metadata"
      aria-label={asset.alt_text || "Shared video"}
    />
  ) : (
    <img
      src={mediaUrl(asset)}
      alt={asset.alt_text || "Shared photo"}
      loading="lazy"
    />
  );
}
export function PostMedia({
  items,
  reel = false,
}: {
  items: Asset[];
  reel?: boolean;
}) {
  const [index, setIndex] = useState(0);
  const asset = items[index] || items[0];
  return (
    <div className={`post-media ${reel ? "reel-media" : ""}`}>
      <MediaView asset={asset} autoplay={reel} />
      {items.length > 1 && (
        <>
          <span className="media-counter">
            {index + 1} / {items.length}
          </span>
          <div className="media-arrows">
            <button
              className="round"
              aria-label="Previous photo"
              disabled={index === 0}
              onClick={() => setIndex(index - 1)}
            >
              <ChevronLeft />
            </button>
            <button
              className="round"
              aria-label="Next photo"
              disabled={index === items.length - 1}
              onClick={() => setIndex(index + 1)}
            >
              <ChevronRight />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
export function ReportDialog({
  type,
  id,
  onClose,
}: {
  type: "post" | "comment" | "user";
  id: string;
  onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const toast = useToast();
  const action = useAction(() =>
    mutate("/reports", "POST", { target_type: type, target_id: id, reason }),
  );
  return (
    <Modal title={`Report ${type}`} onClose={onClose}>
      <p className="muted">
        Tell our moderation team what’s wrong. Your report is private.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          action.mutate(undefined, {
            onSuccess: () => {
              toast("Report submitted for review");
              onClose();
            },
          });
        }}
      >
        <label>
          Reason
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            minLength={5}
            maxLength={1000}
            required
            rows={4}
          />
        </label>
        <ErrorNote error={action.error} />
        <button className="button" disabled={action.isPending}>
          Submit report
        </button>
      </form>
    </Modal>
  );
}
export function FollowButton({ user }: { user: User }) {
  const me = useMe();
  const q = useQuery({
    queryKey: ["profile", user.username],
    queryFn: () => api<Profile>(`/users/${user.username}`),
    enabled: user.id !== me.id,
  });
  const active = q.data?.is_following || q.data?.follow_requested;
  const action = useAction(() =>
    mutate(`/users/${user.id}/follow`, active ? "DELETE" : "POST"),
  );
  if (me.id === user.id) return null;
  return (
    <div className="follow-control">
      <button
        className={`button small ${active ? "secondary" : ""}`}
        disabled={q.isPending || action.isPending || !!q.error}
        onClick={() => action.mutate()}
      >
        {action.isPending
          ? "Working…"
          : q.data?.is_following
            ? "Following"
            : q.data?.follow_requested
              ? "Requested"
              : "Follow"}
      </button>
      <ErrorNote error={action.error || q.error} />
    </div>
  );
}
export function CommentList({ post }: { post: Post }) {
  const me = useMe();
  const [body, setBody] = useState("");
  const [reply, setReply] = useState<Comment | null>(null);
  const [report, setReport] = useState<Comment | null>(null);
  const [edit, setEdit] = useState<Comment | null>(null);
  const [editText, setEditText] = useState("");
  const [remove, setRemove] = useState<Comment | null>(null);
  const q = usePages<Comment>(`/posts/${post.id}/comments`);
  const create = useAction(() =>
    mutate(`/posts/${post.id}/comments`, "POST", {
      body,
      parent_id: reply?.id || null,
    }),
  );
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
  return (
    <section className="comments">
      <h3>
        Conversation <span className="muted">{post.comments_count}</span>
      </h3>
      <ErrorNote error={q.error} retry={() => q.refetch()} />
      {q.isPending && <Spinner />}
      {q.data?.pages
        .flatMap((p) => p.items)
        .map((c) => (
          <div className={`comment ${c.parent_id ? "reply" : ""}`} key={c.id}>
            <Avatar user={c.author} size={32} />
            <div>
              <Link to={`/u/${c.author.username}`}>
                <strong>{c.author.username}</strong>
              </Link>
              {c.parent_id && <small className="muted"> · Reply</small>}
              <p>{c.body}</p>
              <div className="comment-actions">
                <small>{dateLabel(c.created_at)}</small>
                <button onClick={() => setReply(c)}>Reply</button>
                <button
                  aria-label="Like comment"
                  aria-pressed={c.is_liked}
                  disabled={action.isPending}
                  onClick={() =>
                    action.mutate({
                      path: `/comments/${c.id}/like`,
                      method: c.is_liked ? "DELETE" : "PUT",
                    })
                  }
                >
                  <Heart
                    size={13}
                    fill={c.is_liked ? "currentColor" : "none"}
                  />{" "}
                  {c.likes_count || ""}
                </button>
                {c.author.id === me.id && (
                  <button
                    aria-label="Edit comment"
                    onClick={() => {
                      setEdit(c);
                      setEditText(c.body);
                    }}
                  >
                    <Pencil size={13} />
                  </button>
                )}
                {(c.author.id === me.id || post.author.id === me.id) && (
                  <button
                    aria-label="Delete comment"
                    onClick={() => setRemove(c)}
                  >
                    <Trash2 size={13} />
                  </button>
                )}
                <button
                  aria-label="Report comment"
                  onClick={() => setReport(c)}
                >
                  <Flag size={13} />
                </button>
              </div>
            </div>
          </div>
        ))}
      <LoadMore
        hasNext={q.hasNextPage}
        loading={q.isFetchingNextPage}
        load={() => q.fetchNextPage()}
      />
      {!q.isPending && !q.data?.pages[0].items.length && (
        <p className="muted">Start the conversation.</p>
      )}
      <ErrorNote error={action.error} />
      {reply && (
        <div className="reply-label">
          Replying to @{reply.author.username}
          <button onClick={() => setReply(null)}>Cancel</button>
        </div>
      )}
      <form
        className="comment-composer"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate(undefined, {
            onSuccess: () => {
              setBody("");
              setReply(null);
            },
          });
        }}
      >
        <input
          aria-label="Write a comment"
          placeholder="Add a little to the conversation…"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={1000}
          required
        />
        <button
          className="icon-button accent"
          aria-label="Send comment"
          disabled={create.isPending || !body.trim()}
        >
          <Send size={19} />
        </button>
      </form>
      <ErrorNote error={create.error} />
      {report && (
        <ReportDialog
          type="comment"
          id={report.id}
          onClose={() => setReport(null)}
        />
      )}{" "}
      {edit && (
        <Modal title="Edit comment" onClose={() => setEdit(null)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action.mutate(
                {
                  path: `/comments/${edit.id}`,
                  method: "PATCH",
                  data: { body: editText },
                },
                { onSuccess: () => setEdit(null) },
              );
            }}
          >
            <label>
              Comment
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                maxLength={1000}
                required
              />
            </label>
            <ErrorNote error={action.error} />
            <button className="button" disabled={action.isPending}>
              Save changes
            </button>
          </form>
        </Modal>
      )}
      {remove && (
        <Confirm
          title="Delete comment?"
          message="Replies to this comment will also be removed."
          onClose={() => setRemove(null)}
          action={() =>
            action.mutate(
              { path: `/comments/${remove.id}`, method: "DELETE" },
              { onSuccess: () => setRemove(null) },
            )
          }
          busy={action.isPending}
          error={action.error}
        />
      )}
    </section>
  );
}
export function PostCard({
  post,
  expanded = false,
  reel = false,
}: {
  post: Post;
  expanded?: boolean;
  reel?: boolean;
}) {
  const me = useMe();
  const navigate = useNavigate();
  const toast = useToast();
  const [comments, setComments] = useState(expanded);
  const [menu, setMenu] = useState(false);
  const [report, setReport] = useState(false);
  const [edit, setEdit] = useState(false);
  const [caption, setCaption] = useState(post.caption);
  const [remove, setRemove] = useState(false);
  const [collect, setCollect] = useState(false);
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
  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: () => api<{ items: Collection[] }>("/collections"),
    enabled: collect,
  });
  async function share() {
    const url = `${window.location.origin}/p/${post.id}`;
    try {
      if (navigator.share)
        await navigator.share({ title: "A moment on Luma", url });
      else {
        await navigator.clipboard.writeText(url);
        toast("Post link copied");
      }
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError"))
        toast("Could not share. Open the post and copy its URL.");
    }
  }
  return (
    <article className="post-card">
      <header className="post-header">
        <Person user={post.author} />
        <span className="post-date">{dateLabel(post.created_at)}</span>
        <div className="menu-wrap">
          <button
            className="icon-button"
            aria-label="Post options"
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            <MoreHorizontal />
          </button>
          {menu && (
            <div className="dropdown">
              <Link to={`/p/${post.id}`} onClick={() => setMenu(false)}>
                Open post
              </Link>
              <button
                onClick={() => {
                  setCollect(true);
                  setMenu(false);
                }}
              >
                <FolderPlus size={16} /> Add to collection
              </button>
              {post.author.id === me.id && (
                <>
                  <button
                    onClick={() => {
                      setEdit(true);
                      setMenu(false);
                    }}
                  >
                    <Pencil size={16} /> Edit caption
                  </button>
                  <button
                    className="danger-text"
                    onClick={() => {
                      setRemove(true);
                      setMenu(false);
                    }}
                  >
                    <Trash2 size={16} /> Delete post
                  </button>
                </>
              )}
              <button
                onClick={() => {
                  setReport(true);
                  setMenu(false);
                }}
              >
                <Flag size={16} /> Report post
              </button>
            </div>
          )}
        </div>
      </header>
      <PostMedia items={post.media} reel={reel} />
      <div className="post-body">
        <div className="post-actions">
          <button
            className={post.is_liked ? "liked" : ""}
            aria-label={post.is_liked ? "Unlike post" : "Like post"}
            aria-pressed={post.is_liked}
            disabled={action.isPending}
            onClick={() =>
              action.mutate({
                path: `/posts/${post.id}/like`,
                method: post.is_liked ? "DELETE" : "PUT",
              })
            }
          >
            <Heart fill={post.is_liked ? "currentColor" : "none"} />
            <span>{post.likes_count || ""}</span>
          </button>
          <button
            aria-label="Show comments"
            aria-expanded={comments}
            onClick={() => setComments(!comments)}
          >
            <MessageCircle />
            <span>{post.comments_count || ""}</span>
          </button>
          <button aria-label="Share post" onClick={share}>
            <Send />
          </button>
          <button
            className="save-action"
            aria-label={post.is_saved ? "Unsave post" : "Save post"}
            aria-pressed={post.is_saved}
            disabled={action.isPending}
            onClick={() =>
              action.mutate({
                path: `/posts/${post.id}/save`,
                method: post.is_saved ? "DELETE" : "PUT",
              })
            }
          >
            <Bookmark fill={post.is_saved ? "currentColor" : "none"} />
          </button>
        </div>
        <p className="caption">
          <Link to={`/u/${post.author.username}`}>
            <strong>{post.author.username}</strong>
          </Link>{" "}
          {post.caption.split(/(#[a-zA-Z0-9_]+)/g).map((s, i) =>
            s.startsWith("#") ? (
              <Link
                key={i}
                className="hashtag"
                to={`/explore?tag=${s.slice(1)}`}
              >
                {s}
              </Link>
            ) : (
              s
            ),
          )}
        </p>
        {!comments && (
          <button className="subtle-link" onClick={() => setComments(true)}>
            {post.comments_count
              ? `View ${post.comments_count} comments`
              : "Start a conversation"}
          </button>
        )}
        <ErrorNote error={action.error} />
        {comments && <CommentList post={post} />}
      </div>
      {report && (
        <ReportDialog
          type="post"
          id={post.id}
          onClose={() => setReport(false)}
        />
      )}{" "}
      {edit && (
        <Modal title="Edit your caption" onClose={() => setEdit(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action.mutate(
                {
                  path: `/posts/${post.id}`,
                  method: "PATCH",
                  data: { caption },
                },
                {
                  onSuccess: () => {
                    setEdit(false);
                    toast("Caption updated");
                  },
                },
              );
            }}
          >
            <label>
              Caption
              <textarea
                rows={5}
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                maxLength={2200}
              />
            </label>
            <ErrorNote error={action.error} />
            <button className="button" disabled={action.isPending}>
              Save changes
            </button>
          </form>
        </Modal>
      )}
      {remove && (
        <Confirm
          title="Delete this post?"
          message="This will remove the post and its comments."
          onClose={() => setRemove(false)}
          busy={action.isPending}
          error={action.error}
          action={() =>
            action.mutate(
              { path: `/posts/${post.id}`, method: "DELETE" },
              {
                onSuccess: () => {
                  setRemove(false);
                  if (expanded) navigate("/home");
                  toast("Post deleted");
                },
              },
            )
          }
        />
      )}{" "}
      {collect && (
        <Modal title="Add to a collection" onClose={() => setCollect(false)}>
          <ErrorNote error={collections.error || action.error} />
          {collections.isPending && <Spinner />}
          {collections.data?.items.map((c) => (
            <button
              className="collection-option"
              key={c.id}
              disabled={action.isPending}
              onClick={() =>
                action.mutate(
                  {
                    path: `/collections/${c.id}/posts/${post.id}`,
                    method: "PUT",
                  },
                  {
                    onSuccess: () => {
                      toast("Added to collection");
                      setCollect(false);
                    },
                  },
                )
              }
            >
              <FolderPlus size={20} />
              {c.name}
              <ChevronRight size={16} />
            </button>
          ))}
          {collections.data?.items.length === 0 && (
            <p>
              Create a collection in <Link to="/saved">Saved</Link>, then add
              this post.
            </p>
          )}
        </Modal>
      )}
    </article>
  );
}
export function StoriesCarousel() {
  const me = useMe();
  const q = usePages<Story>("/stories/feed");
  const [active, setActive] = useState<Story | null>(null);
  const rows = q.data?.pages.flatMap((p) => p.items) || [];
  return (
    <section className="stories-section">
      <div className="section-eyebrow">LITTLE WINDOWS INTO TODAY</div>
      <div className="stories-carousel">
        <Link className="story" to="/create?kind=story">
          <span className="story-circle create-story">
            <Plus />
          </span>
          <span>Your story</span>
        </Link>
        {rows.map((s) => (
          <button className="story" key={s.id} onClick={() => setActive(s)}>
            <span className={`story-circle ${s.is_viewed ? "viewed" : ""}`}>
              <Avatar user={s.author} size={58} />
            </span>
            <span>{s.author.id === me.id ? "You" : s.author.username}</span>
          </button>
        ))}
        {q.hasNextPage && (
          <button
            className="story"
            disabled={q.isFetchingNextPage}
            onClick={() => q.fetchNextPage()}
          >
            <span className="story-circle">
              <ChevronRight />
            </span>
            More
          </button>
        )}
        {!q.isPending && !rows.length && (
          <p className="muted story-empty">
            A story lasts a day.
            <br />A connection lasts longer.
          </p>
        )}
      </div>
      <ErrorNote error={q.error} />
      {active && (
        <StoryViewer
          story={active}
          onClose={() => setActive(null)}
          next={() => {
            const i = rows.findIndex((s) => s.id === active.id);
            setActive(rows[i + 1] || null);
          }}
        />
      )}
    </section>
  );
}
function StoryViewer({
  story,
  onClose,
  next,
}: {
  story: Story;
  onClose: () => void;
  next: () => void;
}) {
  const me = useMe();
  const [viewers, setViewers] = useState(false);
  const mark = useAction(() => mutate(`/stories/${story.id}/view`));
  const remove = useAction(() => mutate(`/stories/${story.id}`, "DELETE"));
  const people = useQuery({
    queryKey: ["viewers", story.id],
    queryFn: () => api<Page<User>>(`/stories/${story.id}/viewers`),
    enabled: viewers,
  });
  useEffect(() => {
    mark.mutate(); /* Mark only when the displayed story changes. */
  }, [story.id]);
  return (
    <Modal title={`${story.author.username} · today`} onClose={onClose}>
      <div className="story-viewer">
        <MediaView asset={story.media} />
      </div>
      <p>{story.caption}</p>
      <ErrorNote error={mark.error || remove.error} />
      <div className="button-row">
        {story.author.id === me.id && (
          <>
            <button
              className="button secondary"
              onClick={() => setViewers(!viewers)}
            >
              Viewers
            </button>
            <button
              className="button secondary"
              disabled={remove.isPending}
              onClick={() => remove.mutate(undefined, { onSuccess: onClose })}
            >
              Delete story
            </button>
          </>
        )}
        <button className="button" onClick={next}>
          Next story <ChevronRight size={16} />
        </button>
      </div>
      {viewers && (
        <>
          <ErrorNote error={people.error} />
          {people.data?.items.map((u) => (
            <Person key={u.id} user={u} />
          ))}
          {people.data?.items.length === 0 && <p>No views yet.</p>}
        </>
      )}
    </Modal>
  );
}
