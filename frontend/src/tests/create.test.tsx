import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect } from "vitest";
import Create from "../features/posts/Create";
import { upload, mutate } from "../lib/api";
vi.mock("../lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../lib/api")>();
  return { ...mod, upload: vi.fn(), mutate: vi.fn() };
});
function setup() {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Routes>
          <Route path="/" element={<Create />} />
          <Route path="/p/p1" element={<p>Created post detail</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
test("post creation uploads media, submits metadata, and opens the result", async () => {
  URL.createObjectURL = vi.fn(() => "blob:test");
  URL.revokeObjectURL = vi.fn();
  vi.mocked(upload).mockResolvedValue({
    id: "m1",
    url: "/api/v1/media/m1",
    mime_type: "image/jpeg",
    width: 10,
    height: 10,
    status: "ready",
  });
  vi.mocked(mutate).mockResolvedValue({ id: "p1" });
  setup();
  expect(screen.getByRole("button", { name: "Share post" })).toBeDisabled();
  const file = new File(["image bytes"], "picture.png", { type: "image/png" });
  await userEvent.upload(screen.getByLabelText("Choose media"), file);
  await userEvent.type(screen.getByLabelText("Alt text"), "A mountain");
  await userEvent.type(screen.getByLabelText(/Tell the story/), "Hello world");
  await userEvent.click(screen.getByRole("button", { name: "Share post" }));
  await waitFor(() =>
    expect(upload).toHaveBeenCalledWith(file, expect.any(Function)),
  );
  expect(mutate).toHaveBeenCalledWith("/posts", "POST", {
    caption: "Hello world",
    kind: "post",
    media: [{ media_id: "m1", alt_text: "A mountain" }],
  });
  expect(await screen.findByText("Created post detail")).toBeVisible();
});
test("oversized media is rejected before upload", async () => {
  setup();
  const file = new File(["a"], "large.png", { type: "image/png" });
  Object.defineProperty(file, "size", { value: 31 * 1024 * 1024 });
  await userEvent.upload(screen.getByLabelText("Choose media"), file);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "30 MB or smaller",
  );
  expect(screen.getByRole("button", { name: "Share post" })).toBeDisabled();
});
