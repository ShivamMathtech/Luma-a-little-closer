import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowUpRight, Camera, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { usePages } from "../../lib/query";
import type { Post, SearchResult } from "../../types/api";
import {
  PostCard,
  StoriesCarousel,
  MediaView,
  FollowButton,
} from "../../components/Social";
import {
  Person,
  Spinner,
  ErrorNote,
  Empty,
  LoadMore,
} from "../../components/ui";
import { useMe } from "../auth/Auth";
export function PostList({
  path,
  reel = false,
}: {
  path: string;
  reel?: boolean;
}) {
  const q = usePages<Post>(path);
  const rows = q.data?.pages.flatMap((p) => p.items) || [];
  return (
    <>
      <ErrorNote error={q.error} retry={() => q.refetch()} />
      {q.isPending ? (
        <Spinner />
      ) : rows.length ? (
        <div className="post-list">
          {rows.map((p) => (
            <PostCard key={p.id} post={p} reel={reel} />
          ))}
        </div>
      ) : (
        <Empty
          title="There’s room for a new perspective."
          text="Follow a few people or share your first moment."
          action={
            <Link className="button secondary" to="/explore">
              Explore Luma <ArrowUpRight size={16} />
            </Link>
          }
        />
      )}
      <LoadMore
        hasNext={q.hasNextPage}
        loading={q.isFetchingNextPage}
        load={() => q.fetchNextPage()}
      />
    </>
  );
}
export function Suggestions() {
  const q = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api<SearchResult>("/search"),
  });
  return (
    <aside className="discovery-column">
      <div className="discovery-intro">
        <span className="eyebrow">A SMALL REMINDER</span>
        <h2>
          There’s a story
          <br />
          in your <em>everyday.</em>
        </h2>
        <p>Share a glimpse of what makes your world yours.</p>
        <Link to="/create">
          Make a little moment <ArrowUpRight size={16} />
        </Link>
        <Camera className="intro-camera" size={70} strokeWidth={0.8} />
      </div>
      <div className="section-heading">
        <h3>People to discover</h3>
        <Link to="/explore">See all</Link>
      </div>
      {q.data?.users.slice(0, 4).map((u) => (
        <Person user={u} key={u.id}>
          <FollowButton user={u} />
        </Person>
      ))}
      {q.data?.users.length === 0 && (
        <p className="muted">
          Your community starts with you. Invite a friend to join.
        </p>
      )}
      <ErrorNote error={q.error} />
      <div className="sidebar-footer">
        A little closer, every day.
        <br />
        <span>© {new Date().getFullYear()} Luma</span>
      </div>
    </aside>
  );
}
export function Home() {
  const me = useMe();
  return (
    <div className="home-layout">
      <main className="feed-column">
        <header className="page-heading">
          <div>
            <span className="eyebrow">YOUR DAILY DOSE OF CONNECTION</span>
            <h1>
              A little closer<span className="accent">.</span>
            </h1>
            <p>Good to see you, {me.display_name.split(" ")[0]}.</p>
          </div>
          <Link className="button small" to="/create">
            <Camera size={17} /> Share a moment
          </Link>
        </header>
        <StoriesCarousel />
        <div className="feed-tabs">
          <span className="active">Following</span>
          <Link to="/explore">
            For the curious <ArrowUpRight size={14} />
          </Link>
        </div>
        <PostList path="/feed" />
      </main>
      <Suggestions />
    </div>
  );
}
export function Explore() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("q") || "");
  const [debounced, setDebounced] = useState(search);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(t);
  }, [search]);
  const tag = params.get("tag");
  const people = useQuery({
    queryKey: ["search", debounced],
    queryFn: () =>
      api<SearchResult>("/search?q=" + encodeURIComponent(debounced)),
    enabled: !!debounced,
  });
  const posts = usePages<Post>(
    tag ? `/hashtags/${encodeURIComponent(tag)}/posts` : "/explore",
  );
  return (
    <main className="wide-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">FOLLOW YOUR CURIOSITY</span>
          <h1>{tag ? `#${tag}` : "A world of perspectives."}</h1>
          <p>Meet someone new. Find something that stays with you.</p>
        </div>
      </header>
      <label className="search-bar">
        <Search size={21} />
        <input
          aria-label="Search people and hashtags"
          placeholder="Search people, interests, and #hashtags"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      {tag && (
        <button className="chip" onClick={() => setParams({})}>
          Clear #{tag} ×
        </button>
      )}
      {debounced && (
        <section className="search-results">
          <ErrorNote error={people.error} />
          {people.isPending && <Spinner />}
          {people.data?.users.map((u) => (
            <Person user={u} key={u.id}>
              <FollowButton user={u} />
            </Person>
          ))}
          <div className="chips">
            {people.data?.hashtags.map((h) => (
              <button
                key={h.tag}
                className="chip"
                onClick={() => {
                  setParams({ tag: h.tag });
                  setSearch("");
                }}
              >
                #{h.tag} · {h.count}
              </button>
            ))}
          </div>
          {people.data &&
            !people.data.users.length &&
            !people.data.hashtags.length && (
              <p className="muted">No matches. Try another name or interest.</p>
            )}
        </section>
      )}
      <div className="section-heading">
        <h3>{tag ? "In this conversation" : "Fresh perspectives"}</h3>
        <span className="muted">Latest moments</span>
      </div>
      <ErrorNote error={posts.error} retry={() => posts.refetch()} />
      {posts.isPending && <Spinner />}
      <div className="explore-grid">
        {posts.data?.pages
          .flatMap((p) => p.items)
          .map((p) => (
            <Link className="explore-tile" to={`/p/${p.id}`} key={p.id}>
              <MediaView asset={p.media[0]} preview />
              <div>
                <strong>@{p.author.username}</strong>
                <span>♡ {p.likes_count}</span>
              </div>
            </Link>
          ))}
      </div>
      {posts.data?.pages[0].items.length === 0 && (
        <Empty
          title="Every community begins somewhere."
          text="Be the first to share a moment."
          action={
            <Link className="button" to="/create">
              Create a post
            </Link>
          }
        />
      )}
      <LoadMore
        hasNext={posts.hasNextPage}
        loading={posts.isFetchingNextPage}
        load={() => posts.fetchNextPage()}
      />
    </main>
  );
}
export function PostDetail() {
  const { id } = useParams();
  const q = useQuery({
    queryKey: ["post", id],
    queryFn: () => api<Post>(`/posts/${id}`),
  });
  return (
    <main className="narrow-page">
      <Link className="back-link" to="/home">
        ← Back to your feed
      </Link>
      <ErrorNote error={q.error} retry={() => q.refetch()} />
      {q.isPending && <Spinner />}
      {q.data && <PostCard post={q.data} expanded />}
    </main>
  );
}
export function Reels() {
  return (
    <main className="narrow-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">LIFE IN MOTION</span>
          <h1>Little films. Big feelings.</h1>
          <p>A fresh perspective, one reel at a time.</p>
        </div>
      </header>
      <PostList path="/explore?kind=reel" reel />
    </main>
  );
}
