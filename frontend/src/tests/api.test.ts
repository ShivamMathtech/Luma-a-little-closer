import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";

afterEach(() => vi.unstubAllGlobals());

describe("API response validation", () => {
  it("rejects an HTML fallback returned with a successful HTTP status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<!doctype html><html></html>", {
          status: 200,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    await expect(api("/auth/me")).rejects.toMatchObject({
      status: 502,
      message: "The service returned an invalid response. Please try again.",
    });
  });

  it("rejects an application error even when HTTP reports success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({
          ok: false,
          error: { message: "Please retry this operation." },
        }),
      ),
    );

    await expect(api("/auth/me")).rejects.toMatchObject({
      status: 502,
      message: "Please retry this operation.",
    });
  });
});
