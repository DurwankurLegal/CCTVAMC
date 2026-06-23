import { describe, it, expect } from "vitest";
import { filterTenantMenu, type MenuEntry } from "./menu";
import type { AuthUser } from "../store/authSlice";

const menu: MenuEntry[] = [
  { key: "/dashboard", label: "Dashboard" },                       // always shown
  { key: "/customers", label: "Customers", perm: "customers:read" },
  { key: "/users", label: "Users & Roles", perm: "users:write" },
];

function user(partial: Partial<AuthUser>): AuthUser {
  return { id: "1", email: "u@x.com", role: "viewer", is_platform_admin: false, ...partial };
}

describe("filterTenantMenu", () => {
  it("always shows entries without a permission requirement", () => {
    const out = filterTenantMenu(menu, user({ permissions: [] }));
    expect(out.map((m) => m.key)).toContain("/dashboard");
  });

  it("shows only entries the user has permission for", () => {
    const out = filterTenantMenu(menu, user({ role: "technician", permissions: ["customers:read"] }));
    const keys = out.map((m) => m.key);
    expect(keys).toContain("/customers");
    expect(keys).not.toContain("/users"); // lacks users:write
  });

  it("grants admin-only items when users:write is present", () => {
    const out = filterTenantMenu(menu, user({ role: "admin", permissions: ["customers:read", "users:write"] }));
    expect(out.map((m) => m.key)).toContain("/users");
  });

  it("falls back to role check before permissions load (admin keeps items)", () => {
    const out = filterTenantMenu(menu, user({ role: "admin", permissions: undefined }));
    expect(out.map((m) => m.key)).toContain("/users");
  });

  it("hides permissioned items for a viewer before permissions load", () => {
    const out = filterTenantMenu(menu, user({ role: "viewer", permissions: undefined }));
    expect(out.map((m) => m.key)).not.toContain("/users");
  });

  it("returns nothing extra for a null user beyond unpermissioned items", () => {
    const out = filterTenantMenu(menu, null);
    expect(out.map((m) => m.key)).toEqual(["/dashboard"]);
  });
});
