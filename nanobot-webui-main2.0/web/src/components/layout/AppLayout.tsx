import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { MobileBottomTabs } from "./MobileBottomTabs";
import { MobileTopBar } from "./MobileTopBar";
import { SetupGuideDialog } from "../shared/SetupGuideDialog";
import { useIsMobile } from "../../hooks/useIsMobile";
import { useChatStore } from "../../stores/chatStore";
import { useIOSInputFix } from "../../hooks/useIOSInputFix";
import { cn } from "../../lib/utils";

export default function AppLayout() {
  const headStripHeight = 10;
  const { pathname } = useLocation();
  const isChatPage = pathname.startsWith("/chat");
  const [collapsed, setCollapsed] = useState(false);
  const isMobile = useIsMobile();
  const mobileShowChat = useChatStore((s) => s.mobileShowChat);
  // Fixes iOS keyboard zoom + layout restore
  useIOSInputFix();

  return (
    <div
      className="flex overflow-hidden bg-background"
      // position: fixed anchors the app to the screen, so iOS page-scroll
      // triggered by keyboard can't displace the layout.
      // --vvh (set by useIOSInputFix) shrinks the height to the area above the
      // keyboard so the chat input always sits at the keyboard edge.
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        height: "var(--vvh, 100dvh)",
        paddingTop: `${headStripHeight}px`,
      }}
    >
      <div
        className="pointer-events-none absolute top-0 left-0 right-0 z-50 overflow-hidden"
        style={{ height: `${headStripHeight}px` }}
      >
        <img
          src="/head.png?v=20260403-1"
          alt=""
          className="block h-full w-full object-fill"
        />
      </div>
      {/* Sidebar: desktop only */}
      {!isMobile && (
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
      )}

      {/* Top bar: mobile only. Hidden only when inside a chat window (which has its own back-button header) */}
      {isMobile && !mobileShowChat && <MobileTopBar />}

      <main
        className={cn(
          "relative flex-1 min-w-0",
          isChatPage
            ? "flex flex-col overflow-hidden"
            : cn("overflow-auto", isMobile ? "p-3 pt-14" : "p-5"),
        )}
        style={
          isMobile
            ? {
                // Dynamic bottom padding: leaves room for the fixed tab bar (56px) when
                // keyboard is hidden, and shrinks to 0 as keyboard height grows.
                // max(0px, 3.5rem - var(--keyboard-height)) achieves this in pure CSS.
                paddingTop: isChatPage ? undefined : `calc(${headStripHeight}px + 3.5rem)`,
                paddingBottom: "max(env(safe-area-inset-bottom, 0px), calc(3.5rem - var(--keyboard-height, 0px)))",
              }
            : undefined
        }
      >
        <Outlet />
      </main>

      <SetupGuideDialog />

      {/* Bottom tabs: mobile only */}
      {isMobile && <MobileBottomTabs />}
    </div>
  );
}
