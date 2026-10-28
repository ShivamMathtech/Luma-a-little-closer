import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { vi, test, expect, beforeEach } from "vitest";
import { PostCard, FollowButton, PostMedia } from "../components/Social";
import { PostList, Explore } from "../features/feed/Feed";
import { api, mutate } from "../lib/api";
import type { User, Post } from "../types/api";
const me: User = {
  id: "u1",
  username: "alice",
  display_name: "Alice",
  bio: "",
  website: "",
  avatar_id: null,
  is_private: false,
};
const author: User = { ...me, id: "u2", username: "bob", display_name: "Bob" };
const post: Post = {
  id: "p1",
  author,
  caption: "A lovely day #nature",
  kind: "post",
  created_at: "2026-10-28T10:00:00Z",
  media: [
    {
      id: "m1",
      url: "/api/v1/media/m1",
      mime_type: "image/jpeg",
      width: 100,
      height: 100,
      status: "ready",
      alt_text: "Sunlit hill",
    },
  ],
  likes_count: 2,
  comments_count: 0,
  is_liked: false,
  is_saved: false,
};
vi.mock("../features/auth/Auth", () => ({
  useMe: () => ({
    id: "u1",
    username: "alice",
    display_name: "Alice",
    role: "user",
  }),
}));
vi.mock("../lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../lib/api")>();
  return { ...mod, api: vi.fn(), mutate: vi.fn() };
});
beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(mutate).mockReset();
  vi.mocked(mutate).mockResolvedValue({ ok: true });
});
function wrapper(child: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{child}</MemoryRouter>
    </QueryClientProvider>,
  );
}
test("post renders accessible media and real engagement count", () => {
  wrapper(<PostCard post={post} />);
  expect(screen.getByAltText("Sunlit hill")).toBeVisible();
  expect(screen.getByRole("button", { name: "Like post" })).toHaveTextContent(
    "2",
  );
  expect(screen.getByRole("link", { name: "#nature" })).toHaveAttribute(
    "href",
    "/explore?tag=nature",
  );
});
test("like and save call their backend mutations", async () => {
  wrapper(<PostCard post={post} />);
  await userEvent.click(screen.getByRole("button", { name: "Like post" }));
  await waitFor(() =>
    expect(mutate).toHaveBeenCalledWith("/posts/p1/like", "PUT", undefined),
  );
  await userEvent.click(screen.getByRole("button", { name: "Save post" }));
  await waitFor(() =>
    expect(mutate).toHaveBeenCalledWith("/posts/p1/save", "PUT", undefined),
  );
});
test("failed like leaves the original count and reports the error", async () => {
  vi.mocked(mutate).mockRejectedValue(new Error("Try again later"));
  wrapper(<PostCard post={post} />);
  await userEvent.click(screen.getByRole("button", { name: "Like post" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Try again later");
  expect(screen.getByRole("button", { name: "Like post" })).toHaveTextContent(
    "2",
  );
});
test("comment composer sends body and reply context", async () => {
  vi.mocked(api).mockResolvedValue({ items: [], next_cursor: null });
  wrapper(<PostCard post={post} expanded />);
  await userEvent.type(screen.getByLabelText("Write a comment"), "Beautiful!");
  await userEvent.click(screen.getByRole("button", { name: "Send comment" }));
  await waitFor(() =>
    expect(mutate).toHaveBeenCalledWith("/posts/p1/comments", "POST", {
      body: "Beautiful!",
      parent_id: null,
    }),
  );
});
test("follow control uses backend relationship state", async () => {
  vi.mocked(api).mockResolvedValue({
    ...author,
    is_following: true,
    follow_requested: false,
  });
  wrapper(<FollowButton user={author} />);
  const button = await screen.findByRole("button", { name: "Following" });
  await userEvent.click(button);
  await waitFor(() =>
    expect(mutate).toHaveBeenCalledWith("/users/u2/follow", "DELETE"),
  );
});
test("empty feed provides an explore route", async () => {
  vi.mocked(api).mockResolvedValue({ items: [], next_cursor: null });
  wrapper(<PostList path="/feed" />);
  expect(
    await screen.findByText("There’s room for a new perspective."),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: "Explore Luma" })).toHaveAttribute(
    "href",
    "/explore",
  );
});
test("feed renders API posts and retry state", async () => {
  vi.mocked(api).mockResolvedValue({ items: [post], next_cursor: null });
  wrapper(<PostList path="/feed" />);
  expect(await screen.findByAltText("Sunlit hill")).toBeVisible();
});
test("media carousel supports previous and next controls", async () => {
  wrapper(
    <PostMedia
      items={[
        post.media[0],
        { ...post.media[0], id: "m2", alt_text: "Second hill" },
      ]}
    />,
  );
  expect(screen.getByRole("button", { name: "Previous photo" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Next photo" }));
  expect(screen.getByAltText("Second hill")).toBeVisible();
  expect(screen.getByRole("button", { name: "Next photo" })).toBeDisabled();
});
test("search waits for input and displays server matches", async () => {
  vi.mocked(api).mockImplementation(async (path) =>
    path.startsWith("/search")
      ? { users: [author], hashtags: [] }
      : path.startsWith("/users")
        ? { ...author, is_following: false }
        : { items: [], next_cursor: null },
  );
  wrapper(<Explore />);
  await userEvent.type(
    screen.getByLabelText("Search people and hashtags"),
    "bob",
  );
  expect(await screen.findByText("@bob")).toBeVisible();
  expect(api).toHaveBeenCalledWith("/search?q=bob");
});
