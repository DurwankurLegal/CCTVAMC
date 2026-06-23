import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
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
    const { getByText, getByPlaceholderText, getByRole } = renderLogin();
    expect(getByText("CCTV AMC Platform")).toBeInTheDocument();
    expect(getByPlaceholderText("Email")).toBeInTheDocument();
    expect(getByPlaceholderText("Password")).toBeInTheDocument();
    expect(getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });
});
