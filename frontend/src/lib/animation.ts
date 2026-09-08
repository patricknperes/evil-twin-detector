export const animationTokens = {
  duration: {
    fast: 0.18,
    base: 0.32,
    slow: 0.62,
  },
  motionEase: [0.22, 1, 0.36, 1] as const,
  gsapEase: "power3.out",
} as const;

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }

  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
