import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";
import authReducer from "../store/authSlice";
import LoginPage from "./LoginPage";

// apiClient hits import.meta.env at import time and would make network calls;
// mock it so the component renders in isolation.
vi.mock("../api/client", () => ({ default: { post: vi.fn(), get: vi.fn() } }));

function renderLogin() {
  const store = configureStore({ reducer: { auth: authReducer } });
  return render(
    <Provider store={store}>
      <MemoryRouter><LoginPage /></MemoryRouter>
    </Provider>
  );
}

describe("LoginPage", () => {
  it("renders the sign-in form", () => {
    renderLogin();
    expect(screen.getByText("CCTV AMC Platform")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });
});
