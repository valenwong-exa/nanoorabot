import { useState } from "react";
import { ChevronDown, ChevronRight, Wrench } from "lucide-react";
import type { ToolCallInfo } from "../../stores/chatStore";

interface ToolCallCardProps {
  tool: ToolCallInfo;
}

export function ToolCallCard({ tool }: ToolCallCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-md border border-sky-200/60 bg-sky-50/40 dark:border-sky-900/40 dark:bg-sky-950/15 text-xs">
      <button
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-sky-100/40 dark:hover:bg-sky-900/20 rounded-md transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        <Wrench className="h-3 w-3 shrink-0 text-sky-500 dark:text-sky-400" />
        <span className="font-mono font-medium text-sky-700 dark:text-sky-400">{tool.name}</span>
        {open ? (
          <ChevronDown className="ml-auto h-3 w-3 text-muted-foreground/60" />
        ) : (
          <ChevronRight className="ml-auto h-3 w-3 text-muted-foreground/60" />
        )}
      </button>
      {open && (
        <div className="border-t border-sky-200/50 dark:border-sky-900/30 px-3 py-2 space-y-2">
          {tool.input && (
            <div>
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-sky-500/70">Input</div>
              <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] text-sky-900/80 dark:text-sky-200/70">
                {tool.input}
              </pre>
            </div>
          )}
          {tool.output && (
            <div>
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-sky-500/70">Output</div>
              <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] text-sky-900/80 dark:text-sky-200/70">
                {tool.output}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
