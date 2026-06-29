import { useMemo } from "react";
import { Switch } from "../ui/switch";
import { cn } from "../../lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";

export interface ToolPickerItem {
  id: string;
  name: string;
  kind: "skill" | "mcp";
  description?: string;
  enabled: boolean;
  available: boolean;
}

interface SkillPickerPanelProps {
  items: ToolPickerItem[];
  query: string;
  isLoading?: boolean;
  enabledOnly: boolean;
  availableOnly: boolean;
  onEnabledOnlyChange: (value: boolean) => void;
  onAvailableOnlyChange: (value: boolean) => void;
  onSelectItem: (item: ToolPickerItem) => void;
}

function highlightMatch(text: string, query: string) {
  if (!query.trim()) {
    return text;
  }

  const lowerText = text.toLowerCase();
  const lowerQuery = query.trim().toLowerCase();
  const index = lowerText.indexOf(lowerQuery);

  if (index < 0) {
    return text;
  }

  const before = text.slice(0, index);
  const match = text.slice(index, index + lowerQuery.length);
  const after = text.slice(index + lowerQuery.length);

  return (
    <>
      {before}
      <mark className="rounded bg-amber-200/80 px-0.5 text-foreground dark:bg-amber-500/30">
        {match}
      </mark>
      {after}
    </>
  );
}

export function SkillPickerPanel({
  items,
  query,
  isLoading = false,
  enabledOnly,
  availableOnly,
  onEnabledOnlyChange,
  onAvailableOnlyChange,
  onSelectItem,
}: SkillPickerPanelProps) {
  const normalizedQuery = query.trim().toLowerCase();

  const filteredItems = useMemo(
    () =>
      items
        .filter((item) => (enabledOnly ? item.enabled : true))
        .filter((item) => (availableOnly ? item.available : true))
        .filter((item) =>
          normalizedQuery ? item.name.toLowerCase().includes(normalizedQuery) : true
        )
        .sort((a, b) => a.name.localeCompare(b.name)),
    [availableOnly, enabledOnly, items, normalizedQuery]
  );

  return (
    <div
      className="absolute bottom-full left-0 z-50 mb-3 flex h-[560px] max-h-[70vh] w-full min-w-[320px] max-w-[min(720px,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border bg-background/95 shadow-2xl backdrop-blur"
      style={{ resize: "both" }}
    >
      <div className="border-b px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm font-semibold">Tools</p>
            <p className="text-xs text-muted-foreground">
              Type `/tool` to search workspace skills and MCP servers
            </p>
          </div>
          <span className="rounded-md border px-2 py-0.5 text-[11px] text-muted-foreground">
            workspace skills + mcp
          </span>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-xs">
          <label className="flex items-center gap-2 text-muted-foreground">
            <Switch checked={enabledOnly} onCheckedChange={onEnabledOnlyChange} />
            <span>Enabled</span>
          </label>
          <label className="flex items-center gap-2 text-muted-foreground">
            <Switch checked={availableOnly} onCheckedChange={onAvailableOnlyChange} />
            <span>Available</span>
          </label>
          <span className="ml-auto text-muted-foreground">
            {filteredItems.length} result{filteredItems.length === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-3">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Loading tools...
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            No matching tools.
          </div>
        ) : (
          <TooltipProvider delayDuration={150}>
            <div
              className="grid gap-3"
              style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}
            >
              {filteredItems.map((item) => (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => onSelectItem(item)}
                      className={cn(
                        "flex min-h-[70px] flex-col items-start justify-center rounded-xl border px-3 py-3 text-left transition-colors",
                        "hover:border-primary/40 hover:bg-primary/5"
                      )}
                    >
                      <span className="font-mono text-sm font-semibold leading-5">
                        {highlightMatch(item.name, query)}
                      </span>
                      <span className="mt-1 text-xs lowercase text-muted-foreground">
                        {item.enabled ? "enabled" : "disabled"} {item.available ? "available" : "unavailable"}
                      </span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-sm whitespace-pre-wrap">
                    {item.description?.trim() || item.name}
                  </TooltipContent>
                </Tooltip>
              ))}
            </div>
          </TooltipProvider>
        )}
      </div>
    </div>
  );
}
