import { useEffect } from "react";

/**
 * iOS Safari keyboard / zoom fix for web-app-like behavior.
 *
 * Problem 1 — Page zooms on input focus and doesn't unzoom after blur.
 *   Fix: dynamically add `maximum-scale=1` while an input is focused (prevents
 *   zoom), then remove it on blur (restores user pinch-zoom).
 *
 * Problem 2 — When keyboard opens, iOS scrolls the page to bring the focused
 *   input into view, which displaces the entire layout.
 *   Fix: set the app wrapper to `position: fixed` (AppLayout) so it is always
 *   anchored to the screen top, ignoring any page scroll.
 *   We still track `visualViewport.height` → `--vvh` so the wrapper shrinks to
 *   the exact visible area above the keyboard.
 */
export function useIOSInputFix() {
  useEffect(() => {
    // ── 1. Track visual viewport height ───────────────────────────────────
    const vv = window.visualViewport;

    const updateVvh = () => {
      const h = vv ? vv.height : window.innerHeight;
      const kh = Math.max(0, window.innerHeight - h);
      document.documentElement.style.setProperty("--vvh", `${h}px`);
      document.documentElement.style.setProperty("--keyboard-height", `${kh}px`);
      // iOS sometimes scrolls the document when the keyboard opens even
      // when the body is position:fixed. Reset any such scroll immediately.
      if (window.scrollY !== 0 || window.scrollX !== 0) {
        window.scrollTo(0, 0);
      }
    };

    if (vv) {
      vv.addEventListener("resize", updateVvh);
      // visualViewport "scroll" fires when iOS pans the viewport (offsetTop changes)
      vv.addEventListener("scroll", updateVvh);
    }
    window.addEventListener("resize", updateVvh);
    updateVvh();

    // ── 2. Prevent / restore zoom around input focus ─────────────────────
    // iOS zooms when focused element font-size < 16 px. Even with 16 px text
    // some devices still zoom on occasion. Lock maximum-scale while focused.
    const getViewportMeta = () =>
      document.querySelector<HTMLMetaElement>('meta[name="viewport"]');

    const isInput = (el: EventTarget | null) =>
      el instanceof HTMLElement && el.matches("input, textarea, select");

    const onFocus = (e: FocusEvent) => {
      if (!isInput(e.target)) return;
      const meta = getViewportMeta();
      if (!meta || meta.content.includes("maximum-scale")) return;
      meta.content += ", maximum-scale=1";
    };

    const onBlur = (e: FocusEvent) => {
      if (!isInput(e.target)) return;
      const meta = getViewportMeta();
      if (!meta) return;
      // Strip the temporary maximum-scale we added on focus
      meta.content = meta.content.replace(/,?\s*maximum-scale=\S*/g, "").trim();
    };

    document.addEventListener("focus", onFocus, true);
    document.addEventListener("blur", onBlur, true);

    return () => {
      if (vv) {
        vv.removeEventListener("resize", updateVvh);
        vv.removeEventListener("scroll", updateVvh);
      }
      window.removeEventListener("resize", updateVvh);
      document.removeEventListener("focus", onFocus, true);
      document.removeEventListener("blur", onBlur, true);
    };
  }, []);
}
