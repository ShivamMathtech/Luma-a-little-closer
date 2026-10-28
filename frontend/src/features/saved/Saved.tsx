import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FolderPlus, Pencil, Trash2 } from "lucide-react";
import { api, mutate } from "../../lib/api";
import { useAction } from "../../lib/query";
import type { Collection, Post } from "../../types/api";
import { usePages } from "../../lib/query";
import { PostCard } from "../../components/Social";
import {
  Modal,
  ErrorNote,
  Spinner,
  Empty,
  LoadMore,
  Confirm,
} from "../../components/ui";
export default function Saved() {
  const [selected, setSelected] = useState<Collection | null>(null);
  const [editing, setEditing] = useState<Collection | "new" | null>(null);
  const [name, setName] = useState("");
  const [remove, setRemove] = useState(false);
  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: () => api<{ items: Collection[] }>("/collections"),
  });
  const posts = usePages<Post>(
    selected ? `/collections/${selected.id}/posts` : "/saved",
  );
  const action = useAction(
    ({
      path,
      method,
      body,
    }: {
      path: string;
      method: string;
      body?: unknown;
    }) => mutate<Collection>(path, method, body),
  );
  return (
    <main className="narrow-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">KEEP A LITTLE INSPIRATION</span>
          <h1>Worth coming back to.</h1>
          <p>Your saved moments and private collections.</p>
        </div>
        <button
          className="icon-button"
          aria-label="Create collection"
          onClick={() => {
            setEditing("new");
            setName("");
          }}
        >
          <FolderPlus />
        </button>
      </header>
      <div className="chips">
        <button
          className={`chip ${!selected ? "selected" : ""}`}
          onClick={() => setSelected(null)}
        >
          All saved
        </button>
        {collections.data?.items.map((c) => (
          <button
            className={`chip ${selected?.id === c.id ? "selected" : ""}`}
            key={c.id}
            onClick={() => setSelected(c)}
          >
            {c.name}
          </button>
        ))}
      </div>
      {selected && (
        <div className="section-heading">
          <h3>{selected.name}</h3>
          <div>
            <button
              className="icon-button"
              aria-label="Rename collection"
              onClick={() => {
                setEditing(selected);
                setName(selected.name);
              }}
            >
              <Pencil size={17} />
            </button>
            <button
              className="icon-button"
              aria-label="Delete collection"
              onClick={() => setRemove(true)}
            >
              <Trash2 size={17} />
            </button>
          </div>
        </div>
      )}
      <ErrorNote error={collections.error || posts.error || action.error} />
      {posts.isPending && <Spinner />}
      {posts.data?.pages
        .flatMap((p) => p.items)
        .map((p) => (
          <div key={p.id}>
            <PostCard post={p} />
            {selected && (
              <button
                className="subtle-link remove-from"
                disabled={action.isPending}
                onClick={() =>
                  action.mutate({
                    path: `/collections/${selected.id}/posts/${p.id}`,
                    method: "DELETE",
                  })
                }
              >
                Remove from collection
              </button>
            )}
          </div>
        ))}
      {posts.data?.pages[0].items.length === 0 && (
        <Empty
          title="Make room for inspiration."
          text="Save a post with its bookmark, or use its menu to add it to a collection."
        />
      )}
      <LoadMore
        hasNext={posts.hasNextPage}
        loading={posts.isFetchingNextPage}
        load={() => posts.fetchNextPage()}
      />
      {editing && (
        <Modal
          title={
            editing === "new" ? "Create a collection" : "Rename collection"
          }
          onClose={() => setEditing(null)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action.mutate(
                {
                  path:
                    editing === "new"
                      ? "/collections"
                      : `/collections/${editing.id}`,
                  method: editing === "new" ? "POST" : "PATCH",
                  body: { name },
                },
                {
                  onSuccess: (c) => {
                    setSelected(c);
                    setEditing(null);
                  },
                },
              );
            }}
          >
            <label>
              Name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={60}
              />
            </label>
            <ErrorNote error={action.error} />
            <button className="button" disabled={action.isPending}>
              Save collection
            </button>
          </form>
        </Modal>
      )}
      {remove && selected && (
        <Confirm
          title="Delete this collection?"
          message="Your saved posts will remain in All saved."
          onClose={() => setRemove(false)}
          busy={action.isPending}
          error={action.error}
          action={() =>
            action.mutate(
              { path: `/collections/${selected.id}`, method: "DELETE" },
              {
                onSuccess: () => {
                  setSelected(null);
                  setRemove(false);
                },
              },
            )
          }
        />
      )}
    </main>
  );
}
