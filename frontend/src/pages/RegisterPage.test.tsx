import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RegisterPage from "./RegisterPage";
import { AuthProvider } from "../context/AuthContext";
import * as authApi from "../api/auth";

function renderRegister() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <RegisterPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders all registration fields", () => {
    renderRegister();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it("shows error when full name is empty", async () => {
    renderRegister();
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/full name is required/i);
    });
  });

  it("shows error when passwords do not match", async () => {
    renderRegister();
    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: "Jane Smith" },
    });
    fireEvent.change(screen.getByLabelText(/^email/i), {
      target: { value: "jane@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/^password/i), {
      target: { value: "password123" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "different123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/passwords do not match/i);
    });
  });

  it("shows error when password is too short", async () => {
    renderRegister();
    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: "Jane Smith" },
    });
    fireEvent.change(screen.getByLabelText(/^email/i), {
      target: { value: "jane@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/^password/i), {
      target: { value: "short" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "short" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/at least 8 characters/i);
    });
  });

  it("shows API error on duplicate email", async () => {
    vi.spyOn(authApi, "register").mockRejectedValueOnce(
      new Error("An account with this email already exists."),
    );
    renderRegister();
    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: "Jane Smith" },
    });
    fireEvent.change(screen.getByLabelText(/^email/i), {
      target: { value: "dup@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/^password/i), {
      target: { value: "password123" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("has a link to the login page", () => {
    renderRegister();
    expect(screen.getByRole("link", { name: /sign in/i })).toBeInTheDocument();
  });
});
