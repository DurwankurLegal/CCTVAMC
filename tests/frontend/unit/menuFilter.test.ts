/**
 * Unit tests — filterTenantMenu utility
 * ========================================
 * Covers all branches: no perm (always shown), perm with permissions array,
 *                       perm without permissions (role fallback), null user.
 */
import { describe, it, expect } from "vitest";
import { filterTenantMenu, type MenuEntry } from "../../../frontend/src/utils/menu";
import type { AuthUser } from "../../../frontend/src/store/authSlice";

const ALL_MENU: MenuEntry[] = [
  { key: "/dashboard", label: "Dashboard" },                                // no perm → always shown
  { key: "/customers",  label: "Customers",      perm: "customers:read" },
  { key: "/invoices",   label: "Invoices",       perm: "invoices:read" },
  { key: "/users",      label: "Users & Roles",  perm: "users:write" },
  { key: "/reports",    label: "Reports",        perm: "reports:read" },
];

function makeUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: "u1",
    email: "user@test.com",
    role: "staff",
    is_platform_admin: false,
    permissions: [],
    ...overrides,
  };
}

// ── null user ─────────────────────────────────────────────────────────────────

describe("filterTenantMenu — null user", () => {
  it("shows only items without a perm when user is null", () => {
    const result = filterTenantMenu(ALL_MENU, null);
    expect(result.map((m) => m.key)).toEqual(["/dashboard"]);
  });
});

// ── permissions array ─────────────────────────────────────────────────────────

describe("filterTenantMenu — with permissions array", () => {
  it("shows items without perm always", () => {
    const user = makeUser({ permissions: [] });
    const result = filterTenantMenu(ALL_MENU, user);
    expect(result.some((m) => m.key === "/dashboard")).toBe(true);
  });

  it("shows item when user has matching permission", () => {
    const user = makeUser({ permissions: ["customers:read"] });
    const result = filterTenantMenu(ALL_MENU, user);
    expect(result.some((m) => m.key === "/customers")).toBe(true);
  });

  it("hides item when user lacks permission", () => {
    const user = makeUser({ permissions: ["customers:read"] });
    const result = filterTenantMenu(ALL_MENU, user);
    expect(result.some((m) => m.key === "/invoices")).toBe(false);
  });

  it("shows multiple items matching permissions", () => {
    const user = makeUser({ permissions: ["customers:read", "invoices:read"] });
    const result = filterTenantMenu(ALL_MENU, user);
    const keys = result.map((m) => m.key);
    expect(keys).toContain("/customers");
    expect(keys).toContain("/invoices");
  });

  it("hides all permissioned items when permissions array is empty", () => {
    const user = makeUser({ permissions: [] });
    const result = filterTenantMenu(ALL_MENU, user);
    expect(result).toHaveLength(1); // only /dashboard
  });

  it("shows all items when user has all permissions", () => {
    const user = makeUser({
      permissions: ["customers:read", "invoices:read", "users:write", "reports:read"],
    });
    const result = filterTenantMenu(ALL_MENU, user);
    expect(result).toHaveLength(ALL_MENU.length);
  });
});

// ── Role fallback (no permissions array) ─────────────────────────────────────

describe("filterTenantMenu — role fallback", () => {
  it("admin role sees all items even without permissions array", () => {
    const user = makeUser({ role: "admin", permissions: undefined });
    const result = filterTenantMenu(ALL_MENU, user);
    // admin fallback → all shown
    expect(result).toHaveLength(ALL_MENU.length);
  });

  it("manager role sees all items via fallback", () => {
    const user = makeUser({ role: "manager", permissions: undefined });
    const result = filterTenantMenu(ALL_MENU, user);
    expect(result).toHaveLength(ALL_MENU.length);
  });

  it("staff role without permissions sees only no-perm items", () => {
    const user = makeUser({ role: "staff", permissions: undefined });
    const result = filterTenantMenu(ALL_MENU, user);
    expect(result.map((m) => m.key)).toEqual(["/dashboard"]);
  });

  it("platform admin sees all items regardless", () => {
    const user = makeUser({ is_platform_admin: true, permissions: undefined });
    const result = filterTenantMenu(ALL_MENU, user);
    expect(result).toHaveLength(ALL_MENU.length);
  });
});

// ── Edge cases ────────────────────────────────────────────────────────────────

describe("filterTenantMenu — edge cases", () => {
  it("empty menu returns empty array", () => {
    const user = makeUser({ permissions: ["customers:read"] });
    expect(filterTenantMenu([], user)).toEqual([]);
  });

  it("menu with all no-perm items returns all items for null user", () => {
    const menu = [
      { key: "/a", label: "A" },
      { key: "/b", label: "B" },
    ];
    expect(filterTenantMenu(menu, null)).toHaveLength(2);
  });

  it("preserves original menu entry shape", () => {
    const user = makeUser({ permissions: ["customers:read"] });
    const result = filterTenantMenu(ALL_MENU, user);
    const cust = result.find((m) => m.key === "/customers");
    expect(cust?.label).toBe("Customers");
    expect(cust?.perm).toBe("customers:read");
  });
});
