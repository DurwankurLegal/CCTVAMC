import type { AuthUser } from "../store/authSlice";

export interface MenuEntry {
  key: string;
  label: string;
  perm?: string;
}

/**
 * Decide which tenant menu entries a user may see.
 *  - entries without a `perm` are always shown (e.g. Dashboard)
 *  - if effective permissions are loaded, show only entries the user holds
 *  - before permissions load, fall back to the legacy role check so admins
 *    don't briefly lose their admin-only items
 */
export function hasPerm(user: AuthUser | null, perm?: string): boolean {
  if (!perm) return true;
  const perms = user?.permissions;
  if (perms) return perms.includes(perm);
  // Before permissions load, fall back to the legacy role check.
  return !!user?.is_platform_admin || user?.role === "admin" || user?.role === "manager";
}

export function filterTenantMenu<T extends MenuEntry>(menu: T[], user: AuthUser | null): T[] {
  return menu.filter((m) => hasPerm(user, m.perm));
}
