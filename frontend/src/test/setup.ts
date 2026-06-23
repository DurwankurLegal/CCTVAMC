import "@testing-library/jest-dom";
import { vi } from "vitest";

// Ant Design reads window.matchMedia (responsive util); jsdom doesn't implement it.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
});

// jsdom lacks getComputedStyle scrollbar measurement used by some AntD components.
if (!window.matchMedia) window.matchMedia = (() => ({ matches: false })) as any;
