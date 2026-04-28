import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";

interface ThinkingBlockProps {
  content: string;
}

export function ThinkingBlock({ content }: ThinkingBlockProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="my-2 rounded-md border border-amber-200/60 bg-amber-50/40 dark:border-amber-800/40 dark:bg-amber-950/20 text-xs">
      <button
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-amber-700 dark:text-amber-400 hover:text-amber-900 dark:hover:text-amber-200"
        onClick={() => setOpen((v) => !v)}
      >
        <Brain className="h-3 w-3 shrink-0" />
        <span className="font-medium">Thinking</span>
        {open ? (
          <ChevronDown className="ml-auto h-3 w-3" />
        ) : (
          <ChevronRight className="ml-auto h-3 w-3" />
        )}
      </button>
      {open && (
        <div className="border-t border-amber-200/60 dark:border-amber-800/40 px-3 py-2">
          <pre className="whitespace-pre-wrap break-all font-mono text-xs text-amber-800 dark:text-amber-300">
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}
