import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ImagePlus,
  X,
  ArrowUpRight,
  Film,
  CircleDashed,
  Images,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { upload, mutate } from "../../lib/api";
import { ErrorNote, useToast } from "../../components/ui";
import type { Asset, Post } from "../../types/api";
type Selection = { file: File; url: string; alt: string; asset?: Asset };
export default function Create() {
  const [params, setParams] = useSearchParams();
  const kind =
    params.get("kind") === "story"
      ? "story"
      : params.get("kind") === "reel"
        ? "reel"
        : "post";
  const [files, setFiles] = useState<Selection[]>([]);
  const [caption, setCaption] = useState("");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const latest = useRef(files);
  latest.current = files;
  useEffect(
    () => () => latest.current.forEach((f) => URL.revokeObjectURL(f.url)),
    [],
  );
  function pick(list: FileList | null) {
    if (!list) return;
    setError(undefined);
    const selected = Array.from(list);
    const max = kind === "post" ? 10 : 1;
    if (selected.length + files.length > max) {
      setError(
        new Error(`Choose up to ${max} ${max === 1 ? "file" : "files"}.`),
      );
      return;
    }
    if (selected.some((f) => f.size > 30 * 1024 * 1024)) {
      setError(new Error("Each file must be 30 MB or smaller."));
      return;
    }
    setFiles([
      ...files,
      ...selected.map((file) => ({
        file,
        url: URL.createObjectURL(file),
        alt: "",
      })),
    ]);
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      const ready = [...files];
      for (let i = 0; i < ready.length; i++) {
        if (!ready[i].asset) {
          ready[i] = {
            ...ready[i],
            asset: await upload(ready[i].file, (value) =>
              setProgress(Math.round(((i + value / 100) / ready.length) * 100)),
            ),
          };
          setFiles([...ready]);
        }
      }
      if (kind === "story") {
        await mutate("/stories", "POST", {
          media_id: ready[0].asset!.id,
          caption,
        });
        navigate("/home");
      } else {
        const post = await mutate<Post>("/posts", "POST", {
          caption,
          kind,
          media: ready.map((f) => ({ media_id: f.asset!.id, alt_text: f.alt })),
        });
        navigate(`/p/${post.id}`);
      }
      qc.invalidateQueries();
      toast(
        kind === "story"
          ? "Your story is live for 24 hours"
          : "Your moment has been shared",
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="narrow-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">YOUR PERSPECTIVE MATTERS</span>
          <h1>Make a little moment.</h1>
          <p>It doesn’t have to be perfect. It just has to be you.</p>
        </div>
      </header>
      <div className="segmented">
        {(
          [
            { id: "post", icon: Images, label: "Post" },
            { id: "story", icon: CircleDashed, label: "Story" },
            { id: "reel", icon: Film, label: "Reel" },
          ] as const
        ).map((k) => (
          <button
            className={kind === k.id ? "active" : ""}
            key={k.id}
            disabled={busy}
            onClick={() => {
              files.forEach((f) => URL.revokeObjectURL(f.url));
              setFiles([]);
              setParams({ kind: k.id });
              setError(undefined);
            }}
          >
            <k.icon size={17} />
            {k.label}
          </button>
        ))}
      </div>
      <form className="panel create-panel" onSubmit={submit}>
        <label
          className="upload-zone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            if (!busy) pick(e.dataTransfer.files);
          }}
        >
          <ImagePlus size={42} strokeWidth={1.3} />
          <strong>Drop a little of your world here.</strong>
          <span>Click to browse or drag a file</span>
          <small>
            {kind === "reel"
              ? "MP4 or WebM video · up to 3 minutes"
              : "JPEG, PNG, WebP, MP4 or WebM"}{" "}
            · 30 MB per file
          </small>
          <input
            type="file"
            aria-label="Choose media"
            accept={
              kind === "reel"
                ? "video/mp4,video/webm"
                : "image/jpeg,image/png,image/webp,video/mp4,video/webm"
            }
            multiple={kind === "post"}
            disabled={busy}
            onChange={(e) => {
              pick(e.target.files);
              e.target.value = "";
            }}
          />
        </label>
        <div className="upload-previews">
          {files.map((f, i) => (
            <div key={f.url}>
              <div className="upload-preview">
                {f.file.type.startsWith("video/") ? (
                  <video src={f.url} controls />
                ) : (
                  <img src={f.url} alt="Upload preview" />
                )}
                <button
                  type="button"
                  className="round"
                  aria-label={`Remove ${f.file.name}`}
                  disabled={busy}
                  onClick={() => {
                    URL.revokeObjectURL(f.url);
                    setFiles(files.filter((_, n) => n !== i));
                  }}
                >
                  <X size={16} />
                </button>
              </div>
              {kind !== "story" && (
                <label>
                  Alt text
                  <input
                    placeholder="Describe this moment for everyone"
                    value={f.alt}
                    maxLength={300}
                    disabled={busy}
                    onChange={(e) =>
                      setFiles(
                        files.map((x, n) =>
                          n === i ? { ...x, alt: e.target.value } : x,
                        ),
                      )
                    }
                  />
                </label>
              )}
            </div>
          ))}
        </div>
        <label>
          {kind === "story" ? "A few words" : "Tell the story"}
          <textarea
            placeholder="What’s the story behind this moment? #findyourpeople"
            rows={4}
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            maxLength={kind === "story" ? 300 : 2200}
            disabled={busy}
          />
          <small className="muted">
            {caption.length} / {kind === "story" ? 300 : 2200}
          </small>
        </label>
        {kind === "story" && (
          <p className="muted">
            Stories disappear from your community’s view after 24 hours.
          </p>
        )}
        <ErrorNote error={error} />
        {busy && (
          <div>
            <progress value={progress} max={100} />
            <small>
              {progress < 100
                ? `Uploading ${progress}%`
                : "Finishing your moment…"}
            </small>
          </div>
        )}
        <button className="button wide" disabled={busy || !files.length}>
          {busy ? "Sharing…" : `Share ${kind}`}
          <ArrowUpRight size={18} />
        </button>
      </form>
    </main>
  );
}
