import "@testing-library/jest-dom/vitest";

class ObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Landing-page motion and responsive charts use browser observers that jsdom does not provide.
Object.defineProperty(globalThis, "IntersectionObserver", { writable: true, value: ObserverMock });
Object.defineProperty(globalThis, "ResizeObserver", { writable: true, value: ObserverMock });
