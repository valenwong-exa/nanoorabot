import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Ban,
  ChevronDown,
  ChevronRight,
  Clock3,
  Database,
  Eye,
  FileCode,
  Folder,
  Hash,
  Link2,
  LoaderCircle,
  Package,
  RefreshCw,
  Table2,
  User,
  Users,
  type LucideIcon,
} from "lucide-react";
import {
  loadDatabaseMetadataNode,
  openDatabaseMetadata,
  refreshDatabaseMetadataNode,
} from "../api/databaseMetadataApi";
import { cn } from "../lib/utils";
import type { MetadataTreeNode } from "../types/databaseMetadata";

const DEFAULT_EXPANDED_NODE_IDS = new Set(["root", "schemas", "users"]);
const FORCE_INTERNAL_ICON_NODE_TYPES = new Set([
  "table",
  "index",
  "view",
  "package_spec",
  "package_body",
  "function",
  "procedure",
  "queue",
  "trigger",
  "type",
  "type_body",
  "sequence",
  "materialized_view",
  "synonym",
  "db_link",
  "directory",
  "java_object",
  "scheduler_job",
  "empty",
]);
const REFRESHABLE_NODE_TYPES = new Set([
  "schemas_root",
  "schema",
  "users_root",
  "user",
  "tables_folder",
  "indexes_folder",
  "views_folder",
  "package_specs_folder",
  "package_bodies_folder",
  "functions_folder",
  "procedures_folder",
  "queues_folder",
  "triggers_folder",
  "types_folder",
  "type_bodies_folder",
  "sequences_folder",
  "materialized_views_folder",
  "synonyms_folder",
  "db_links_folder",
  "directories_folder",
  "java_objects_folder",
  "scheduler_jobs_folder",
]);

interface DatabaseMetadataTreeProps {
  connectionId?: string | null;
  sqlclConnectionName?: string | null;
  displayName?: string | null;
  databaseStatus?: string | null;
  className?: string;
}

interface ContextMenuState {
  node: MetadataTreeNode;
  x: number;
  y: number;
}

function getErrorMessage(error: unknown, fallback: string): string {
  return (
    (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
    fallback
  );
}

function isExpandable(node: MetadataTreeNode): boolean {
  return node.loaded === false || (node.children?.length ?? 0) > 0;
}

function getNodeIcon(nodeType: string): LucideIcon {
  switch (nodeType) {
    case "root":
    case "connection":
    case "connection_info":
      return Database;
    case "connected_schema":
    case "schemas_root":
    case "schema":
    case "users_root":
      return Folder;
    case "user":
      return User;
    case "tables_folder":
    case "table":
      return Table2;
    case "indexes_folder":
    case "index":
    case "sequences_folder":
    case "sequence":
      return Hash;
    case "views_folder":
    case "view":
    case "materialized_views_folder":
    case "materialized_view":
      return Eye;
    case "package_specs_folder":
    case "package_spec":
    case "package_bodies_folder":
    case "package_body":
      return Package;
    case "functions_folder":
    case "function":
    case "procedures_folder":
    case "procedure":
    case "queues_folder":
    case "queue":
    case "triggers_folder":
    case "trigger":
    case "types_folder":
    case "type":
    case "type_bodies_folder":
    case "type_body":
    case "java_objects_folder":
    case "java_object":
      return FileCode;
    case "db_links_folder":
    case "db_link":
    case "synonyms_folder":
    case "synonym":
      return Link2;
    case "directories_folder":
    case "directory":
      return Folder;
    case "scheduler_jobs_folder":
    case "scheduler_job":
      return Clock3;
    case "empty":
      return Ban;
    default:
      return Users;
  }
}

function replaceNodeInTree(tree: MetadataTreeNode, updatedNode: MetadataTreeNode): MetadataTreeNode {
  if (tree.id === updatedNode.id) {
    return updatedNode;
  }
  if (!tree.children?.length) {
    return tree;
  }
  return {
    ...tree,
    children: tree.children.map((child) => replaceNodeInTree(child, updatedNode)),
  };
}

function collectAutoExpandedNodeIds(tree: MetadataTreeNode): Set<string> {
  const next = new Set(DEFAULT_EXPANDED_NODE_IDS);
  next.add(tree.id);
  for (const child of tree.children ?? []) {
    next.add(child.id);
  }
  return next;
}

function getRelativeNodePath(node: MetadataTreeNode, displayName?: string | null): string {
  const rawPath =
    typeof node.metadata?.nodePath === "string" && node.metadata.nodePath.trim()
      ? node.metadata.nodePath.trim()
      : node.id;
  const displayPrefix = displayName?.trim()
    ? `Oracle Connections/${displayName.trim()}`
    : "Oracle Connections";

  let relativePath = rawPath;
  if (rawPath.startsWith(displayPrefix)) {
    relativePath = rawPath.slice(displayPrefix.length) || "/";
  } else if (rawPath.startsWith("Oracle Connections")) {
    const pathParts = rawPath.split("/");
    relativePath = pathParts.length > 2 ? `/${pathParts.slice(2).join("/")}` : "/";
  }

  if (!relativePath.startsWith("/")) {
    relativePath = `/${relativePath}`;
  }

  return relativePath;
}

function formatNodePathsForCopy(
  nodes: MetadataTreeNode[],
  sqlclConnectionName?: string | null,
  displayName?: string | null,
): string {
  const connectionName = sqlclConnectionName?.trim() || "unknown";
  const relativePaths = nodes.map((node) => getRelativeNodePath(node, displayName));

  if (relativePaths.length <= 1) {
    return `Please use oracle sqlcl MCP tool to connect to database ${connectionName},  check ${relativePaths[0] ?? "/"}`;
  }

  return [
    `Please use oracle sqlcl MCP tool to connect to database ${connectionName},  then check these paths:`,
    ...relativePaths.map((path) => `- ${path}`),
  ].join("\n");
}

function collectVisibleNodeIds(tree: MetadataTreeNode, expandedNodeIds: Set<string>): string[] {
  const result: string[] = [];

  const visit = (node: MetadataTreeNode) => {
    result.push(node.id);
    if (expandedNodeIds.has(node.id)) {
      for (const child of node.children ?? []) {
        visit(child);
      }
    }
  };

  visit(tree);
  return result;
}

function findNodeById(tree: MetadataTreeNode, nodeId: string): MetadataTreeNode | null {
  if (tree.id === nodeId) {
    return tree;
  }
  for (const child of tree.children ?? []) {
    const found = findNodeById(child, nodeId);
    if (found) {
      return found;
    }
  }
  return null;
}

export function DatabaseMetadataTree({
  connectionId,
  sqlclConnectionName,
  displayName,
  databaseStatus,
  className,
}: DatabaseMetadataTreeProps) {
  const [tree, setTree] = useState<MetadataTreeNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set(DEFAULT_EXPANDED_NODE_IDS));
  const [loadingNodeIds, setLoadingNodeIds] = useState<Set<string>>(new Set());
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [selectedNodeIds, setSelectedNodeIds] = useState<Set<string>>(new Set());
  const [selectionAnchorNodeId, setSelectionAnchorNodeId] = useState<string | null>(null);
  const [missingPngIcons, setMissingPngIcons] = useState<Set<string>>(new Set());
  const normalizedDatabaseStatus = (databaseStatus ?? "").toUpperCase();
  const isInvalidDatabase = normalizedDatabaseStatus === "INVALID";

  useEffect(() => {
    const closeMenu = () => setContextMenu(null);
    window.addEventListener("click", closeMenu);
    window.addEventListener("scroll", closeMenu, true);
    window.addEventListener("resize", closeMenu);
    return () => {
      window.removeEventListener("click", closeMenu);
      window.removeEventListener("scroll", closeMenu, true);
      window.removeEventListener("resize", closeMenu);
    };
  }, []);

  useEffect(() => {
    if (!connectionId || !sqlclConnectionName) {
      setTree(null);
      setError(null);
      setFromCache(false);
      setExpandedNodeIds(new Set(DEFAULT_EXPANDED_NODE_IDS));
      setSelectedNodeIds(new Set());
      setSelectionAnchorNodeId(null);
      return;
    }

    if (isInvalidDatabase) {
      setTree(null);
      setError("Database is invalid");
      setLoading(false);
      setFromCache(false);
      setExpandedNodeIds(new Set(DEFAULT_EXPANDED_NODE_IDS));
      setSelectedNodeIds(new Set());
      setSelectionAnchorNodeId(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    void openDatabaseMetadata({
      connectionId,
      sqlclConnectionName,
      displayName: displayName || connectionId,
    })
      .then((response) => {
        if (cancelled) {
          return;
        }
        setTree(response.tree);
        setFromCache(response.fromCache);
        setExpandedNodeIds(collectAutoExpandedNodeIds(response.tree));
        setSelectedNodeIds(new Set());
        setSelectionAnchorNodeId(null);
      })
      .catch((nextError: unknown) => {
        if (cancelled) {
          return;
        }
        setTree(null);
        setError(getErrorMessage(nextError, "Failed to open database metadata"));
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [connectionId, displayName, isInvalidDatabase, sqlclConnectionName]);

  const canRenderTree = useMemo(() => Boolean(tree && connectionId && sqlclConnectionName), [tree, connectionId, sqlclConnectionName]);
  const visibleNodeIds = useMemo(
    () => (tree ? collectVisibleNodeIds(tree, expandedNodeIds) : []),
    [expandedNodeIds, tree],
  );
  const selectedNodes = useMemo(() => {
    if (!tree) {
      return [] as MetadataTreeNode[];
    }
    return visibleNodeIds
      .filter((nodeId) => selectedNodeIds.has(nodeId))
      .map((nodeId) => findNodeById(tree, nodeId))
      .filter((node): node is MetadataTreeNode => Boolean(node));
  }, [selectedNodeIds, tree, visibleNodeIds]);

  async function handleLoadNode(node: MetadataTreeNode): Promise<void> {
    if (!connectionId || !sqlclConnectionName) {
      return;
    }
    setLoadingNodeIds((prev) => new Set(prev).add(node.id));
    try {
      const response = await loadDatabaseMetadataNode({
        connectionId,
        sqlclConnectionName,
        nodeId: node.id,
        nodeType: node.type,
        schemaName: typeof node.metadata?.schemaName === "string" ? node.metadata.schemaName : undefined,
      });
      setTree((prev) => (prev ? replaceNodeInTree(prev, response.node) : prev));
    } catch (nextError) {
      toast.error(getErrorMessage(nextError, `Failed to load ${node.label}`));
    } finally {
      setLoadingNodeIds((prev) => {
        const next = new Set(prev);
        next.delete(node.id);
        return next;
      });
    }
  }

  async function handleRefreshNode(node: MetadataTreeNode): Promise<void> {
    if (!connectionId || !sqlclConnectionName) {
      return;
    }
    setLoadingNodeIds((prev) => new Set(prev).add(node.id));
    try {
      const response = await refreshDatabaseMetadataNode({
        connectionId,
        sqlclConnectionName,
        nodeId: node.id,
        nodeType: node.type,
        schemaName: typeof node.metadata?.schemaName === "string" ? node.metadata.schemaName : undefined,
      });
      setTree((prev) => (prev ? replaceNodeInTree(prev, response.node) : prev));
      setExpandedNodeIds((prev) => new Set(prev).add(node.id));
      toast.success(`Refreshed ${node.label}`);
      setFromCache(false);
    } catch (nextError) {
      toast.error(getErrorMessage(nextError, `Failed to refresh ${node.label}`));
    } finally {
      setLoadingNodeIds((prev) => {
        const next = new Set(prev);
        next.delete(node.id);
        return next;
      });
      setContextMenu(null);
    }
  }

  async function handleCopy(text: string, label: string) {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(`Copied ${label}`);
    } catch {
      toast.error(`Failed to copy ${label}`);
    } finally {
      setContextMenu(null);
    }
  }

  async function handleToggle(node: MetadataTreeNode) {
    if (!isExpandable(node)) {
      return;
    }
    const isExpanded = expandedNodeIds.has(node.id);
    if (isExpanded) {
      setExpandedNodeIds((prev) => {
        const next = new Set(prev);
        next.delete(node.id);
        return next;
      });
      return;
    }
    if (node.loaded === false && !loadingNodeIds.has(node.id)) {
      await handleLoadNode(node);
    }
    setExpandedNodeIds((prev) => new Set(prev).add(node.id));
  }

  function handleNodeSelection(node: MetadataTreeNode, event: React.MouseEvent<HTMLDivElement>) {
    if (!tree) {
      return;
    }

    const visibleIndex = visibleNodeIds.indexOf(node.id);
    const anchorId = selectionAnchorNodeId ?? node.id;
    const anchorIndex = visibleNodeIds.indexOf(anchorId);

    if (event.shiftKey && anchorIndex >= 0 && visibleIndex >= 0) {
      const start = Math.min(anchorIndex, visibleIndex);
      const end = Math.max(anchorIndex, visibleIndex);
      const rangeNodeIds = visibleNodeIds.slice(start, end + 1);
      setSelectedNodeIds(new Set(rangeNodeIds));
      return;
    }

    if (event.ctrlKey || event.metaKey) {
      setSelectedNodeIds((prev) => {
        const next = new Set(prev);
        if (next.has(node.id)) {
          next.delete(node.id);
        } else {
          next.add(node.id);
        }
        return next;
      });
      setSelectionAnchorNodeId(node.id);
      return;
    }

    setSelectedNodeIds(new Set([node.id]));
    setSelectionAnchorNodeId(node.id);
  }

  function resolveNodesForCopy(targetNode: MetadataTreeNode): MetadataTreeNode[] {
    if (selectedNodeIds.has(targetNode.id) && selectedNodes.length > 1) {
      return selectedNodes;
    }
    return [targetNode];
  }

  function renderNode(node: MetadataTreeNode, depth: number) {
    const expanded = expandedNodeIds.has(node.id);
    const expandable = isExpandable(node);
    const nodePath = typeof node.metadata?.nodePath === "string" ? node.metadata.nodePath : node.id;
    const isRefreshing = loadingNodeIds.has(node.id);
    const isConnectionNode = node.type === "connection";
    const refreshable = REFRESHABLE_NODE_TYPES.has(node.type);
    const Icon = getNodeIcon(node.type);
    const iconName = node.icon?.trim();
    const isSelected = selectedNodeIds.has(node.id);
    const preferPng =
      !FORCE_INTERNAL_ICON_NODE_TYPES.has(node.type) &&
      Boolean(iconName) &&
      !missingPngIcons.has(iconName!);

    return (
      <div key={node.id} className="min-w-max">
        <div
          className={cn(
            "group flex min-w-max items-center gap-1 rounded-md px-1.5 py-1 text-[12px] leading-5 transition-colors hover:bg-muted/70",
            isSelected && "bg-primary/10 text-primary hover:bg-primary/15",
            refreshable && "cursor-default",
          )}
          style={{ paddingLeft: `${depth * 14 + 4}px` }}
          onClick={(event) => handleNodeSelection(node, event)}
          onContextMenu={(event) => {
            event.preventDefault();
            if (!selectedNodeIds.has(node.id)) {
              setSelectedNodeIds(new Set([node.id]));
              setSelectionAnchorNodeId(node.id);
            }
            setContextMenu({
              node,
              x: event.clientX,
              y: event.clientY,
            });
          }}
          title={nodePath}
        >
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              void handleToggle(node);
            }}
            className="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm text-muted-foreground hover:bg-muted"
          >
            {expandable ? (
              expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />
            ) : (
              <span className="h-3.5 w-3.5" />
            )}
          </button>
          {preferPng ? (
            <img
              src={`/database_metadata_icon/${iconName}`}
              alt=""
              className="h-4 w-4 shrink-0"
              draggable={false}
              onError={() => {
                setMissingPngIcons((prev) => {
                  if (prev.has(iconName!)) {
                    return prev;
                  }
                  const next = new Set(prev);
                  next.add(iconName!);
                  return next;
                });
              }}
            />
          ) : (
            <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          <span className="shrink-0 whitespace-nowrap text-foreground">{node.label}</span>
          {isConnectionNode && (
            <span className="ml-1 inline-flex items-center rounded-full bg-emerald-500/12 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
              CONNECTED
            </span>
          )}
          {isRefreshing && <LoaderCircle className="ml-1 h-3.5 w-3.5 animate-spin text-muted-foreground" />}
        </div>
        {expanded && node.children?.length ? (
          <div>{node.children.map((child) => renderNode(child, depth + 1))}</div>
        ) : null}
      </div>
    );
  }

  return (
    <div className={cn("relative flex h-full min-h-0 flex-col", className)}>
      <div className="border-b px-3 py-2">
        <div className="truncate text-sm font-semibold">{displayName || "Database"}</div>
        <div className="mt-0.5 flex items-center gap-2 text-[11px] text-muted-foreground">
          <span>{sqlclConnectionName || "-"}</span>
          {databaseStatus ? (
            <span className="rounded-full border px-1.5 py-0.5">
              {databaseStatus}
            </span>
          ) : null}
          {tree ? (
            <span className="rounded-full border px-1.5 py-0.5">
              {fromCache ? "YAML Cache" : "Live SQLcl"}
            </span>
          ) : null}
        </div>
      </div>

      {!connectionId || !sqlclConnectionName ? (
        <div className="flex flex-1 items-center justify-center px-4 text-center text-xs text-muted-foreground">
          Select a monitored database and click OPEN.
        </div>
      ) : loading ? (
        <div className="flex flex-1 items-center justify-center gap-2 text-xs text-muted-foreground">
          <LoaderCircle className="h-4 w-4 animate-spin" />
          <span>Loading database metadata...</span>
        </div>
      ) : error ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center">
          <p className="text-xs text-rose-600 dark:text-rose-300">{error}</p>
          {!isInvalidDatabase ? (
            <button
              type="button"
              onClick={() => {
                setTree(null);
                setError(null);
                setLoading(true);
                void openDatabaseMetadata({
                  connectionId,
                  sqlclConnectionName,
                  displayName: displayName || connectionId,
                })
                  .then((response) => {
                    setTree(response.tree);
                    setFromCache(response.fromCache);
                    setExpandedNodeIds(collectAutoExpandedNodeIds(response.tree));
                  })
                  .catch((nextError: unknown) => {
                    setError(getErrorMessage(nextError, "Failed to open database metadata"));
                  })
                  .finally(() => setLoading(false));
              }}
              className="rounded-md border px-2 py-1 text-xs transition-colors hover:bg-muted"
            >
              Retry
            </button>
          ) : null}
        </div>
      ) : canRenderTree ? (
        <div className="min-h-0 flex-1 overflow-auto px-2 py-2">
          <div className="min-w-max">{renderNode(tree!, 0)}</div>
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center px-4 text-center text-xs text-muted-foreground">
          No metadata tree is available yet.
        </div>
      )}

      {contextMenu ? (
        <div
          className="fixed z-50 min-w-[160px] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-lg"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            type="button"
            disabled={!REFRESHABLE_NODE_TYPES.has(contextMenu.node.type)}
            onClick={() => void handleRefreshNode(contextMenu.node)}
            className={cn(
              "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent",
              !REFRESHABLE_NODE_TYPES.has(contextMenu.node.type) && "cursor-not-allowed opacity-50 hover:bg-transparent",
            )}
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={() => void handleCopy(contextMenu.node.label, "name")}
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
          >
            <span>Copy Name</span>
          </button>
          <button
            type="button"
            onClick={() =>
              void handleCopy(
                formatNodePathsForCopy(resolveNodesForCopy(contextMenu.node), sqlclConnectionName, displayName),
                selectedNodeIds.has(contextMenu.node.id) && selectedNodes.length > 1 ? "node paths" : "node path",
              )
            }
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
          >
            <span>
              {selectedNodeIds.has(contextMenu.node.id) && selectedNodes.length > 1 ? "Copy Node Paths" : "Copy Node Path"}
            </span>
          </button>
        </div>
      ) : null}
    </div>
  );
}
