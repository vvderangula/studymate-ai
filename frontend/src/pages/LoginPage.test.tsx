import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LoginPage from "./LoginPage";
import { AuthProvider } from "../context/AuthContext";
import * as authApi from "../api/auth";

function renderLogin() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders email and password fields", () => {
    renderLogin();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("shows error when email is empty", async () => {
    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/email is required/i);
    });
  });

  it("shows error when password is empty", async () => {
    renderLogin();
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "user@test.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/password is required/i);
    });
  });

  it("shows API error message on failed login", async () => {
    vi.spyOn(authApi, "login").mockRejectedValueOnce(
      new Error("Invalid email or password."),
    );
    renderLogin();
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "bad@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "wrongpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("has a link to the register page", () => {
    renderLogin();
    expect(screen.getByRole("link", { name: /create one/i })).toBeInTheDocument();
  });
});
