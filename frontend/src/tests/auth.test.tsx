import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect } from "vitest";
import { AuthPage, Protected } from "../features/auth/Auth";
import { api, mutate, ApiError } from "../lib/api";
vi.mock("../lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../lib/api")>();
  return { ...mod, api: vi.fn(), mutate: vi.fn() };
});
function wrapper(child: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{child}</MemoryRouter>
    </QueryClientProvider>,
  );
}
test("login validates required fields before calling the API", async () => {
  wrapper(<AuthPage />);
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByText("Enter your username or email")).toBeVisible();
  expect(mutate).not.toHaveBeenCalled();
});
test("login submits credentials and shows a server error", async () => {
  vi.mocked(mutate).mockRejectedValue(
    new ApiError(401, "Invalid login or password"),
  );
  wrapper(<AuthPage />);
  await userEvent.type(screen.getByLabelText("Username or email"), "alice");
  await userEvent.type(screen.getByLabelText("Password"), "incorrect");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Invalid login or password",
  );
  expect(mutate).toHaveBeenCalledWith("/auth/login", "POST", {
    login: "alice",
    password: "incorrect",
  });
});
test("registration explains weak passwords", async () => {
  wrapper(<AuthPage register />);
  await userEvent.type(screen.getByLabelText("Your name"), "Alice");
  await userEvent.type(screen.getByLabelText("Username"), "alice");
  await userEvent.type(
    screen.getByLabelText("Email address"),
    "alice@example.com",
  );
  await userEvent.type(screen.getByLabelText("Password"), "short");
  await userEvent.click(
    screen.getByRole("button", { name: "Create your account" }),
  );
  expect(await screen.findByText("Use at least 12 characters")).toBeVisible();
});
test("protected routes send unauthenticated visitors to login", async () => {
  vi.mocked(api).mockRejectedValue(new ApiError(401, "Sign in"));
  wrapper(
    <Routes>
      <Route path="/" element={<Protected />}>
        <Route index element={<p>Private feed</p>} />
      </Route>
      <Route path="/login" element={<p>Login destination</p>} />
    </Routes>,
  );
  expect(await screen.findByText("Login destination")).toBeVisible();
  expect(screen.queryByText("Private feed")).not.toBeInTheDocument();
});
test("protected routes expose retry for service failure", async () => {
  vi.mocked(api).mockRejectedValue(new ApiError(503, "Service unavailable"));
  wrapper(
    <Routes>
      <Route path="/" element={<Protected />} />
    </Routes>,
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Service unavailable",
  );
  expect(screen.getByRole("button", { name: "Try again" })).toBeVisible();
});
