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
export function filterTenantMenu<T extends MenuEntry>(menu: T[], user: AuthUser | null): T[] {
  const perms = user?.permissions;
  return menu.filter((m) => {
    if (!m.perm) return true;
    if (perms) return perms.includes(m.perm);
    return !!user?.is_platform_admin || user?.role === "admin" || user?.role === "manager";
  });
}
