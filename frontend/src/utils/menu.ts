import type { AuthUser } from "../store/authSlice";

export interface MenuEntry {
  key: string;
  label: string;
  perm?: string;
  module?: string; // Modular SaaS subscription code check
  children?: MenuEntry[];
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
  const activeModules = user?.subscription?.active_modules;

  return menu
    .map((m) => {
      if (m.children) {
        return {
          ...m,
          children: filterTenantMenu(m.children as T[], user)
        } as T;
      }
      return m;
    })
    .filter((m) => {
      // Guard by permission
      if (!hasPerm(user, m.perm)) {
        return false;
      }

      // Guard by active module subscription (skip check if platform admin)
      if (m.module && !user?.is_platform_admin) {
        if (!activeModules) {
          return false;
        }
        const requiredModules = m.module.split(",").map(s => s.trim());
        const hasAnyModule = requiredModules.some(mod => activeModules.includes(mod));
        if (!hasAnyModule) {
          return false;
        }
      }

      if (m.children && m.children.length === 0) {
        return false;
      }
      return true;
    });
}
