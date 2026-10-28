import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useNavigate } from "react-router-dom";
import {
  Settings,
  MessageCircle,
  Link as LinkIcon,
  Lock,
  MoreHorizontal,
} from "lucide-react";
import { api, mutate } from "../../lib/api";
import { usePages, useAction } from "../../lib/query";
import type { Profile, User } from "../../types/api";
import {
  Avatar,
  Spinner,
  ErrorNote,
  Modal,
  Person,
  Empty,
  LoadMore,
  useToast,
} from "../../components/ui";
import { FollowButton, ReportDialog } from "../../components/Social";
import { PostList } from "../feed/Feed";
import { useMe } from "../auth/Auth";
function FollowList({
  username,
  direction,
  onClose,
}: {
  username: string;
  direction: string;
  onClose: () => void;
}) {
  const q = usePages<User>(`/users/${username}/${direction}`);
  return (
    <Modal
      title={direction === "followers" ? "Followers" : "Following"}
      onClose={onClose}
    >
      <ErrorNote error={q.error} />
      {q.isPending && <Spinner />}
      {q.data?.pages
        .flatMap((p) => p.items)
        .map((u) => (
          <Person user={u} key={u.id}>
            <FollowButton user={u} />
          </Person>
        ))}
      {q.data?.pages[0].items.length === 0 && (
        <p className="muted">No people here yet.</p>
      )}
      <LoadMore
        hasNext={q.hasNextPage}
        loading={q.isFetchingNextPage}
        load={() => q.fetchNextPage()}
      />
    </Modal>
  );
}
export default function ProfilePage() {
  const { username } = useParams();
  const me = useMe();
  const navigate = useNavigate();
  const toast = useToast();
  const q = useQuery({
    queryKey: ["profile", username],
    queryFn: () => api<Profile>(`/users/${username}`),
  });
  const [list, setList] = useState("");
  const [menu, setMenu] = useState(false);
  const [report, setReport] = useState(false);
  const message = useAction(() =>
    mutate<{ id: string }>("/conversations", "POST", { user_id: q.data?.id }),
  );
  const relation = useAction((kind: "block" | "mute") =>
    mutate(`/users/${q.data?.id}/${kind}`, "PUT"),
  );
  const user = q.data;
  if (q.isPending) return <Spinner />;
  if (!user) return <ErrorNote error={q.error} retry={() => q.refetch()} />;
  const own = user.id === me.id;
  const visible = own || !user.is_private || user.is_following;
  return (
    <main className="profile-page">
      <div className="profile-cover">
        <span>A LITTLE MORE YOU.</span>
        <div className="cover-sun" />
      </div>
      <section className="profile-header">
        <Avatar user={user} size={108} />
        <div className="profile-controls">
          {own ? (
            <Link className="button secondary" to="/settings">
              <Settings size={16} /> Edit profile
            </Link>
          ) : (
            <>
              <FollowButton user={user} />
              <button
                className="button secondary"
                disabled={message.isPending || !visible}
                title={!visible ? "Follow this private account first" : ""}
                onClick={() =>
                  message.mutate(undefined, {
                    onSuccess: (d) => navigate(`/messages/${d.id}`),
                  })
                }
              >
                <MessageCircle size={16} /> Message
              </button>
              <div className="menu-wrap">
                <button
                  className="icon-button"
                  aria-label="Account options"
                  aria-expanded={menu}
                  onClick={() => setMenu(!menu)}
                >
                  <MoreHorizontal />
                </button>
                {menu && (
                  <div className="dropdown">
                    <button
                      onClick={() => {
                        relation.mutate("mute", {
                          onSuccess: () =>
                            toast(
                              "Account muted. Manage muted accounts in Settings.",
                            ),
                        });
                        setMenu(false);
                      }}
                    >
                      Mute account
                    </button>
                    <button
                      onClick={() =>
                        relation.mutate("block", {
                          onSuccess: () => {
                            toast("Account blocked");
                            navigate("/home");
                          },
                        })
                      }
                    >
                      Block account
                    </button>
                    <button
                      onClick={() => {
                        setReport(true);
                        setMenu(false);
                      }}
                    >
                      Report account
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
        <h1>
          {user.display_name} {user.is_private && <Lock size={20} />}
        </h1>
        <p className="muted">@{user.username}</p>
        <p className="bio">
          {user.bio ||
            (own
              ? "Tell people a little about yourself in your profile settings."
              : "")}
        </p>
        {user.website && (
          <a
            className="profile-website"
            href={user.website}
            target="_blank"
            rel="noopener noreferrer"
          >
            <LinkIcon size={15} />
            {user.website.replace(/^https?:\/\//, "")}
          </a>
        )}
        <div className="profile-stats">
          <span>
            <strong>{user.posts_count}</strong> moments
          </span>
          <button disabled={!visible} onClick={() => setList("followers")}>
            <strong>{user.followers_count}</strong> followers
          </button>
          <button disabled={!visible} onClick={() => setList("following")}>
            <strong>{user.following_count}</strong> following
          </button>
        </div>
        <ErrorNote error={message.error || relation.error} />
      </section>
      <div className="profile-posts">
        {visible ? (
          <PostList
            path={`/explore?author=${encodeURIComponent(user.username)}`}
          />
        ) : (
          <Empty
            title="A more private perspective."
            text="Send a follow request to see this person’s moments."
          />
        )}
      </div>
      {list && (
        <FollowList
          username={user.username}
          direction={list}
          onClose={() => setList("")}
        />
      )}{" "}
      {report && (
        <ReportDialog
          type="user"
          id={user.id}
          onClose={() => setReport(false)}
        />
      )}
    </main>
  );
}
