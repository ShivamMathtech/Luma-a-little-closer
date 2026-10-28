import type { Asset } from "../types/api";
export const BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(
  /\/$/,
  "",
);
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}
let csrf = "";
let csrfPending: Promise<string> | null = null;
let refreshPending: Promise<void> | null = null;
async function csrfToken(): Promise<string> {
  if (csrf) return csrf;
  if (!csrfPending)
    csrfPending = fetch(`${BASE}/api/v1/auth/csrf`, { credentials: "include" })
      .then(async (r) => {
        if (!r.ok)
          throw new ApiError(
            r.status,
            "Unable to establish a secure connection",
          );
        csrf = (await r.json()).csrf_token;
        return csrf;
      })
      .finally(() => {
        csrfPending = null;
      });
  return csrfPending;
}
async function parse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.error?.details
      ?.map(
        (e: { field: string; message: string }) =>
          `${e.field.replace("body.", "")}: ${e.message}`,
      )
      .join("; ");
    throw new ApiError(
      response.status,
      detail || data?.error?.message || `Request failed (${response.status})`,
    );
  }
  if (data === null || typeof data !== "object") {
    throw new ApiError(
      502,
      "The service returned an invalid response. Please try again.",
    );
  }
  if (data.ok === false) {
    throw new ApiError(
      502,
      data.error?.message ||
        "The operation could not be completed. Please try again.",
    );
  }
  return data as T;
}
export async function api<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const method = init.method || "GET";
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD"].includes(method))
    headers.set("X-CSRF-Token", await csrfToken());
  const response = await fetch(`${BASE}/api/v1${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });
  if (
    response.status === 401 &&
    retry &&
    ![
      "/auth/login",
      "/auth/register",
      "/auth/refresh",
      "/auth/reset-password",
    ].includes(path)
  ) {
    if (!refreshPending)
      refreshPending = api("/auth/refresh", { method: "POST" }, false)
        .then(() => undefined)
        .finally(() => {
          refreshPending = null;
        });
    await refreshPending;
    return api<T>(path, init, false);
  }
  if (response.status === 403 && retry && !["GET", "HEAD"].includes(method)) {
    const error = await response
      .clone()
      .json()
      .catch(() => null);
    if (error?.error?.message?.includes("CSRF")) {
      csrf = "";
      return api<T>(path, init, false);
    }
  }
  return parse<T>(response);
}
export const mutate = <T>(path: string, method = "POST", body?: unknown) =>
  api<T>(path, {
    method,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
export const mediaUrl = (asset: Pick<Asset, "url">) => BASE + asset.url;
export async function upload(
  file: File,
  progress: (percent: number) => void,
): Promise<Asset> {
  await api("/auth/me");
  const token = await csrfToken();
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/api/v1/media`);
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-CSRF-Token", token);
    xhr.timeout = 120000;
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) progress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onerror = () =>
      reject(new Error("Upload failed. Check your connection and try again."));
    xhr.ontimeout = () =>
      reject(new Error("Upload timed out. Try a smaller file."));
    xhr.onload = () => {
      let data;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        reject(new Error("Upload returned an invalid response"));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else
        reject(
          new ApiError(xhr.status, data?.error?.message || "Upload failed"),
        );
    };
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}
