import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  Ban,
  ChevronDown,
  ChevronRight,
  Clock3,
  Copy,
  Database,
  Eye,
  FileCode,
  Folder,
  Hash,
  Link2,
  LoaderCircle,
  Package,
  RefreshCw,
  Search,
  Table2,
  User,
  Users,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import {
  fetchSourceDdl,
  fetchTableDdl,
  loadDatabaseMetadataNode,
  openDatabaseMetadata,
  refreshDatabaseMetadataNode,
} from "../api/databaseMetadataApi";
import { cn } from "../lib/utils";
import { useChatStore } from "../stores/chatStore";
import type { MetadataTreeNode, OpenDatabaseMetadataResponse } from "../types/databaseMetadata";
import { Dialog, DialogContent, DialogTitle } from "./ui/dialog";

const DEFAULT_EXPANDED_NODE_IDS = new Set(["root", "dbops", "schemas"]);
const TREE_ROW_HEIGHT = 34;
const TREE_OVERSCAN_ROWS = 12;
const LARGE_FOLDER_PAGE_SIZE = 1000;
const LARGE_FOLDER_TYPES = new Set([
  "tables_folder",
  "dictionary_table_folder",
  "indexes_folder",
  "views_folder",
  "dynamic_views_folder",
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
const FILTERABLE_NODE_TYPES = new Set([...LARGE_FOLDER_TYPES, "selectai_root"]);
const FORCE_INTERNAL_ICON_NODE_TYPES = new Set([
  "dbops_root",
  "selectai_root",
  "selectai_profile",
  "table",
  "index",
  "view",
  "dynamic_view",
  "useful_diagnoses_folder",
  "useful_diagnosis",
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
  "dbops_root",
  "selectai_root",
  "schemas_root",
  "schema",
  "users_root",
  "user",
  "tables_folder",
  "indexes_folder",
  "views_folder",
  "dynamic_views_folder",
  "dictionary_table_folder",
  "useful_diagnoses_folder",
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
const SCHEMA_OBJECT_NODE_TYPES = new Set([
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
]);
const DDL_CACHE_FOLDER_BY_NODE_TYPE: Record<string, string> = {
  table: "Tables",
  index: "Indexes",
  view: "Views",
  package_spec: "Package Specs",
  package_body: "Package Bodies",
  function: "Functions",
  procedure: "Procedures",
  queue: "Queues",
  trigger: "Triggers",
  type: "Types",
  type_body: "Type Bodies",
  sequence: "Sequences",
  materialized_view: "Materialized Views",
  synonym: "Synonyms",
  db_link: "DB Links",
  directory: "Directories",
  java_object: "Java Objects",
  scheduler_job: "Scheduler Jobs",
};

interface DatabaseMetadataTreeProps {
  connectionId?: string | null;
  sqlclConnectionName?: string | null;
  displayName?: string | null;
  databaseStatus?: string | null;
  className?: string;
  openNonce?: number;
  onOpenSuccess?: (response: OpenDatabaseMetadataResponse) => void;
}

interface ContextMenuState {
  node: MetadataTreeNode;
  x: number;
  y: number;
}

interface ManualCopyState {
  text: string;
  label: string;
}

interface ObjectViewDialogState {
  node: MetadataTreeNode;
  sqlText: string;
}

interface VisibleNodeRow {
  kind: "node";
  node: MetadataTreeNode;
  depth: number;
}

interface VisibleFolderControlsRow {
  kind: "folder-controls";
  node: MetadataTreeNode;
  depth: number;
  totalChildren: number;
  filteredChildren: number;
  visibleChildren: number;
  filterText: string;
  hasMore: boolean;
}

type VisibleTreeRow = VisibleNodeRow | VisibleFolderControlsRow;

function normalizeCodeLines(text: string): string[] {
  return text.replace(/\r\n/g, "\n").split("\n");
}

function getSelectedTextWithinContainer(container: HTMLElement | null): string {
  if (typeof window === "undefined" || !container) {
    return "";
  }
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
    return "";
  }
  const range = selection.getRangeAt(0);
  const commonAncestor = range.commonAncestorContainer;
  const containingNode =
    commonAncestor.nodeType === Node.TEXT_NODE ? commonAncestor.parentNode : commonAncestor;
  if (!containingNode || !container.contains(containingNode)) {
    return "";
  }
  return selection.toString().replace(/\r\n/g, "\n").trim();
}

function getErrorMessage(error: unknown, fallback: string): string {
  return (
    (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
    fallback
  );
}

function legacyCopyText(text: string): boolean {
  if (typeof document === "undefined") {
    return false;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.top = "-1000px";
  textarea.style.left = "-1000px";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);

  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    document.body.removeChild(textarea);
  }
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
    case "dbops_root":
    case "selectai_root":
      return Wrench;
    case "selectai_profile":
      return User;
    case "schemas_root":
    case "schema":
    case "users_root":
      return Folder;
    case "user":
      return User;
    case "tables_folder":
    case "table":
    case "dictionary_table_folder":
    case "dictionary_table_item":
      return Table2;
    case "indexes_folder":
    case "index":
    case "sequences_folder":
    case "sequence":
      return Hash;
    case "views_folder":
    case "view":
    case "dynamic_views_folder":
    case "dynamic_view":
    case "materialized_views_folder":
    case "materialized_view":
      return Eye;
    case "useful_diagnoses_folder":
    case "useful_diagnosis":
      return Search;
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

function isObjectNamePathNode(node: MetadataTreeNode): boolean {
  return node.type === "dynamic_view" || node.type === "dictionary_table_item";
}

function canCopyNodePath(node: MetadataTreeNode): boolean {
  return node.type !== "dynamic_view" && node.type !== "dictionary_table_item";
}

function formatNodePathsForCopy(
  nodes: MetadataTreeNode[],
  sqlclConnectionName?: string | null,
  displayName?: string | null,
): string {
  const connectionName = sqlclConnectionName?.trim() || "unknown";
  if (nodes.length === 1 && isSelectAiProfileNode(nodes[0])) {
    const profileName =
      typeof nodes[0].metadata?.profileName === "string" && nodes[0].metadata.profileName.trim()
        ? nodes[0].metadata.profileName.trim()
        : nodes[0].label.trim();
    const escapedProfileName = profileName.replace(/'/g, "''");
    return [
      `Use oracle sqlcl MCP tool to connect to database ${connectionName} check profile via`,
      "```sql",
      "with",
      "p as (",
      "  select profile_id,",
      "         dbms_lob.substr(description, 800, 1) as description,",
      "         profile_name,",
      "         status,",
      "         created,",
      "         last_modified",
      "  from   user_cloud_ai_profiles",
      `  where  profile_name = '${escapedProfileName}'`,
      "),",
      "a as (",
      "  select profile_name,",
      "         attribute_name,",
      "         dbms_lob.substr(attribute_value, 700, 1) as attribute_value",
      "  from   user_cloud_ai_profile_attributes",
      `  where  profile_name = '${escapedProfileName}'`,
      "),",
      "attr_txt as (",
      "  select rtrim(",
      "           xmlcast(",
      "             xmlagg(",
      "               xmlelement(",
      "                 e,",
      "                 attribute_name || '=' ||",
      "                 case",
      "                   when regexp_like(attribute_name, 'PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL', 'i')",
      "                   then '[MASKED]'",
      "                   else replace(replace(attribute_value, chr(10), ' '), chr(13), ' ')",
      "                 end || chr(10)",
      "               )",
      "               order by attribute_name",
      "             ) as clob",
      "           ),",
      "           chr(10)",
      "         ) as attributes",
      "  from a",
      "),",
      "txt as (",
      "  select",
      "    'PROFILE_NAME='  || p.profile_name || chr(10) ||",
      "    'DESCRIPTION='   || replace(replace(p.description, chr(10), ' '), chr(13), ' ') || chr(10) ||",
      "    'PROFILE_ID='    || p.profile_id   || chr(10) ||",
      "    'STATUS='        || p.status       || chr(10) ||",
      "    'CREATED='       || to_char(p.created, 'yyyy-mm-dd hh24:mi:ss') || chr(10) ||",
      "    'LAST_MODIFIED=' || to_char(p.last_modified, 'yyyy-mm-dd hh24:mi:ss') || chr(10) ||",
      "    '---- ATTRIBUTES ----' || chr(10) ||",
      "    nvl(dbms_lob.substr(attr_txt.attributes, 2200, 1), 'NO ATTRIBUTES FOUND') as report_text",
      "  from p",
      "  cross join attr_txt",
      ")",
      "select substrb(report_text, 1, 4000) as profile_report",
      "from   txt;",
      "```",
    ].join("\n");
  }
  if (nodes.length > 0 && nodes.every((node) => isObjectNamePathNode(node))) {
    const objectNames = nodes.map((node) => node.label.trim()).filter(Boolean);
    return `Please use oracle sqlcl MCP tool to connect to database ${connectionName}. This is a development task. Use the local metadata or code cache in the workspace when available, and only fetch additional database metadata when needed. Current targets: ${objectNames.join(", ")}. Make the requested changes, then compile or validate affected objects if needed.`;
  }
  const schemaAccessPrefix = formatSchemaAccessPrefix(nodes, sqlclConnectionName);
  const ddlPrefix = formatObjectDdlAvailabilityPrefix(nodes, sqlclConnectionName);
  const relativePaths = nodes.map((node) => getRelativeNodePath(node, displayName));
  const instructionPrefix =
    `Please use oracle sqlcl MCP tool to connect to database ${connectionName}. ` +
    "This is a development task. Prefer the local DDL or code cache in the workspace when available. " +
    "Use SQLcl MCP only when you need additional metadata or need to validate database state. " +
    "If the requested work changes objects, update the relevant local files and compile or validate the affected objects when needed.";

  if (relativePaths.length <= 1) {
    return [
      instructionPrefix,
      `Current target path: ${relativePaths[0] ?? "/"}.`,
      ddlPrefix.trim(),
      schemaAccessPrefix.trim(),
      "For follow-up requests, treat this path as the current development context unless another target is specified.",
    ]
      .filter(Boolean)
      .join("\n\n");
  }

  return [
    instructionPrefix,
    ddlPrefix.trim(),
    schemaAccessPrefix.trim(),
    "Current target paths:",
    ...relativePaths.map((path) => `- ${path}`),
    "For follow-up requests, treat these paths as the current development scope unless another target is specified.",
  ]
    .filter(Boolean)
    .join("\n");
}

function formatNodeNamePromptForCopy(
  node: MetadataTreeNode,
  sqlclConnectionName?: string | null,
  displayName?: string | null,
): string {
  const connectionName = sqlclConnectionName?.trim() || "unknown";
  const objectName =
    typeof node.metadata?.objectName === "string" && node.metadata.objectName.trim()
      ? node.metadata.objectName.trim()
      : node.label.trim();
  if (isSelectAiProfileNode(node)) {
    const profileName =
      typeof node.metadata?.profileName === "string" && node.metadata.profileName.trim()
        ? node.metadata.profileName.trim()
        : node.label.trim();
    return `SelectAI profile ${profileName}(can check it via sqlcl mcp connect to ${connectionName}, \`\`\`sql select profile_name from user_cloud_ai_profiles \`\`\`)`;
  }
  if (node.type === "dictionary_table_item") {
    return `Connect to "${connectionName}" via the SQLcl MCP tool. Check the Dictionary View: ${objectName}. Use the command "DESC ${objectName}" only if needed, and do not show me the definition unless I ask for it.`;
  }
  if (node.type === "dynamic_view") {
    return `Connect to "${connectionName}" via the SQLcl MCP tool. Check the Dynamic Performance View: ${objectName}. Use the command "DESC ${objectName}" only if needed, and do not show me the definition unless I ask for it.`;
  }
  const relativePath = getRelativeNodePath(node, displayName).replace(/^\/+/, "") || node.label.trim() || "/";
  return `Please use oracle sqlcl MCP tool to connect to database ${connectionName}. Current object path: ${relativePath}. For follow-up requests, unless another object is specified, treat this path as the current object context.`;
}

function isSqlCopyNode(node: MetadataTreeNode): boolean {
  return node.type === "useful_diagnosis" && typeof node.metadata?.sqlText === "string";
}

function isSelectAiProfileNode(node: MetadataTreeNode): boolean {
  return node.type === "selectai_profile";
}

function formatDiagnosisSqlForCopy(node: MetadataTreeNode, sqlclConnectionName?: string | null): string {
  const connectionName = sqlclConnectionName?.trim() || "unknown";
  const sqlText = typeof node.metadata?.sqlText === "string" ? node.metadata.sqlText.trim() : "";
  return `Please use oracle sqlcl MCP tool to connect to database ${connectionName},   check ${node.label} through SQL "${sqlText}"`;
}

function isSchemaObjectNode(node: MetadataTreeNode): boolean {
  return SCHEMA_OBJECT_NODE_TYPES.has(node.type);
}

function formatSchemaAccessLine(
  node: MetadataTreeNode,
  sqlclConnectionName?: string | null,
): string | null {
  if (node.type !== "schema") {
    return null;
  }
  const connectionName = sqlclConnectionName?.trim();
  const schemaName =
    typeof node.metadata?.schemaName === "string" ? node.metadata.schemaName.trim() : node.label.trim();
  if (!connectionName || !schemaName) {
    return null;
  }
  return `${schemaName} schema is accessible via the SQLcl MCP tool using connection ${connectionName}. Read the ora-ops-metadata skill for more information.`;
}

function formatSchemaAccessPrefix(
  nodes: MetadataTreeNode[],
  sqlclConnectionName?: string | null,
): string {
  const lines = Array.from(
    new Set(
      nodes
        .map((node) => formatSchemaAccessLine(node, sqlclConnectionName))
        .filter((line): line is string => Boolean(line)),
    ),
  );
  return lines.length > 0 ? `\n${lines.join("\n")}` : "";
}

function formatObjectDdlAvailabilityLine(
  node: MetadataTreeNode,
  sqlclConnectionName?: string | null,
): string | null {
  if (!isSchemaObjectNode(node)) {
    return null;
  }
  const connectionName = sqlclConnectionName?.trim();
  const schemaName =
    typeof node.metadata?.schemaName === "string" ? node.metadata.schemaName.trim() : "";
  const objectName =
    typeof node.metadata?.objectName === "string" ? node.metadata.objectName.trim() : node.label.trim();
  const objectTypeFolder = DDL_CACHE_FOLDER_BY_NODE_TYPE[node.type];
  if (!connectionName || !schemaName || !objectName || !objectTypeFolder) {
    return null;
  }
  return `Local cached DDL is available at <workspace>\\ora-ops-metadata\\metadata_cache\\${connectionName}\\${schemaName}\\${objectTypeFolder}\\${objectName}.sql`;
}

function formatObjectDdlAvailabilityPrefix(
  nodes: MetadataTreeNode[],
  sqlclConnectionName?: string | null,
): string {
  const lines = nodes
    .map((node) => formatObjectDdlAvailabilityLine(node, sqlclConnectionName))
    .filter((line): line is string => Boolean(line));
  return lines.length > 0 ? `${lines.join("\n")}\n\n` : "";
}

function isTableNode(node: MetadataTreeNode): boolean {
  return node.type === "table";
}

function isSourceDdlNode(node: MetadataTreeNode): boolean {
  return (
    node.type === "index" ||
    node.type === "view" ||
    node.type === "trigger" ||
    node.type === "sequence" ||
    node.type === "procedure" ||
    node.type === "function" ||
    node.type === "package_spec" ||
    node.type === "package_body"
  );
}

function formatObjectDdlPrompt(
  node: MetadataTreeNode,
  sqlText: string,
  sqlclConnectionName?: string | null,
  displayName?: string | null,
): string {
  const relativePath = getRelativeNodePath(node, displayName);
  const ddlPrefix = formatObjectDdlAvailabilityPrefix([node], sqlclConnectionName);
  return `${ddlPrefix}Check ${relativePath} DDL below:\n\n${sqlText}`;
}

function formatSelectedCodePrompt(
  node: MetadataTreeNode,
  selectedText: string,
  sqlclConnectionName?: string | null,
  displayName?: string | null,
): string {
  const connectionName = sqlclConnectionName?.trim() || "unknown";
  const relativePath = getRelativeNodePath(node, displayName);
  const ddlPrefix = formatObjectDdlAvailabilityPrefix([node], sqlclConnectionName).trim();
  const parts = [
    `Please use oracle sqlcl MCP tool to connect to database ${connectionName}. Focus on the selected code in ${relativePath}.`,
    `Current object path: ${relativePath}.`,
    ddlPrefix,
    "Use the selected code below as the primary fragment to analyze or modify. Prefer local cache. If you change it, update local files first, then compile or validate and report errors.",
    "Selected code:",
    "```sql",
    selectedText.trim(),
    "```",
  ];
  return parts.filter(Boolean).join("\n\n");
}

function formatSelectedCodeOnly(selectedText: string): string {
  return selectedText.trim();
}

function formatSelectAiProfilePrompt(
  node: MetadataTreeNode,
  sqlclConnectionName?: string | null,
): string {
  const connectionName = sqlclConnectionName?.trim() || "unknown";
  const profileName =
    typeof node.metadata?.profileName === "string" && node.metadata.profileName.trim()
      ? node.metadata.profileName.trim()
      : node.label.trim();
  const escapedProfileName = profileName.replace(/'/g, "''");
  return [
    `Please use the Oracle SQLcl MCP tool to connect to database ${connectionName}.`,
    `Set the current Select AI profile by executing: EXEC DBMS_CLOUD_AI.SET_PROFILE('${escapedProfileName}')`,
  ].join("\n\n");
}

function findParentNode(tree: MetadataTreeNode, targetNodeId: string): MetadataTreeNode | null {
  for (const child of tree.children ?? []) {
    if (child.id === targetNodeId) {
      return tree;
    }
    const nestedParent = findParentNode(child, targetNodeId);
    if (nestedParent) {
      return nestedParent;
    }
  }
  return null;
}

function collectVisibleTreeRows(
  tree: MetadataTreeNode,
  expandedNodeIds: Set<string>,
  folderFilters: Map<string, string>,
  folderVisibleCounts: Map<string, number>,
): VisibleTreeRow[] {
  const result: VisibleTreeRow[] = [];

  const visit = (node: MetadataTreeNode, depth: number) => {
    result.push({ kind: "node", node, depth });
    if (expandedNodeIds.has(node.id)) {
      const rawChildren = node.children ?? [];
      const filterText = folderFilters.get(node.id)?.trim().toLowerCase() ?? "";
      const supportsFilterControls = FILTERABLE_NODE_TYPES.has(node.type);
      const shouldRenderControls = supportsFilterControls && (rawChildren.length > 0 || filterText.length > 0);
      const filteredChildren = shouldRenderControls
        ? rawChildren.filter((child) => child.label.toLowerCase().includes(filterText))
        : rawChildren;
      const visibleChildrenCount = LARGE_FOLDER_TYPES.has(node.type)
        ? Math.min(filteredChildren.length, folderVisibleCounts.get(node.id) ?? LARGE_FOLDER_PAGE_SIZE)
        : filteredChildren.length;

      if (shouldRenderControls) {
        result.push({
          kind: "folder-controls",
          node,
          depth: depth + 1,
          totalChildren: rawChildren.length,
          filteredChildren: filteredChildren.length,
          visibleChildren: visibleChildrenCount,
          filterText: folderFilters.get(node.id) ?? "",
          hasMore: visibleChildrenCount < filteredChildren.length,
        });
      }

      for (const child of filteredChildren.slice(0, visibleChildrenCount)) {
        visit(child, depth + 1);
      }
    }
  };

  visit(tree, 0);
  return result;
}

export function DatabaseMetadataTree({
  connectionId,
  sqlclConnectionName,
  displayName,
  databaseStatus,
  className,
  openNonce,
  onOpenSuccess,
}: DatabaseMetadataTreeProps) {
  const { t } = useTranslation();
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
  const [manualCopyState, setManualCopyState] = useState<ManualCopyState | null>(null);
  const [objectViewDialog, setObjectViewDialog] = useState<ObjectViewDialogState | null>(null);
  const [selectedSourceText, setSelectedSourceText] = useState("");
  const [hasInsertedSelectionContext, setHasInsertedSelectionContext] = useState(false);
  const [folderFilters, setFolderFilters] = useState<Map<string, string>>(new Map());
  const [folderVisibleCounts, setFolderVisibleCounts] = useState<Map<string, number>>(new Map());
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(400);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const manualCopyTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const sourceSelectionContainerRef = useRef<HTMLDivElement | null>(null);
  const sourceSelectionTextRef = useRef("");
  const onOpenSuccessRef = useRef(onOpenSuccess);
  const addDraftSnippet = useChatStore((s) => s.addDraftSnippet);
  const normalizedDatabaseStatus = (databaseStatus ?? "").toUpperCase();
  const isInvalidDatabase = normalizedDatabaseStatus === "INVALID";

  useEffect(() => {
    onOpenSuccessRef.current = onOpenSuccess;
  }, [onOpenSuccess]);

  useEffect(() => {
    const closeMenus = () => {
      setContextMenu(null);
    };
    window.addEventListener("click", closeMenus);
    window.addEventListener("scroll", closeMenus, true);
    window.addEventListener("resize", closeMenus);
    return () => {
      window.removeEventListener("click", closeMenus);
      window.removeEventListener("scroll", closeMenus, true);
      window.removeEventListener("resize", closeMenus);
    };
  }, []);

  useEffect(() => {
    sourceSelectionTextRef.current = "";
    setSelectedSourceText("");
    setHasInsertedSelectionContext(false);
  }, [objectViewDialog]);

  useEffect(() => {
    if (!manualCopyState) {
      return;
    }

    const textarea = manualCopyTextareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.focus();
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);
  }, [manualCopyState]);

  useEffect(() => {
    if (!connectionId || !sqlclConnectionName) {
      setTree(null);
      setError(null);
      setFromCache(false);
      setExpandedNodeIds(new Set(DEFAULT_EXPANDED_NODE_IDS));
      setSelectedNodeIds(new Set());
      setSelectionAnchorNodeId(null);
      setFolderFilters(new Map());
      setFolderVisibleCounts(new Map());
      setScrollTop(0);
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
      setFolderFilters(new Map());
      setFolderVisibleCounts(new Map());
      setScrollTop(0);
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
        onOpenSuccessRef.current?.(response);
        setFromCache(response.fromCache);
        setExpandedNodeIds(collectAutoExpandedNodeIds(response.tree));
        setSelectedNodeIds(new Set());
        setSelectionAnchorNodeId(null);
        setFolderFilters(new Map());
        setFolderVisibleCounts(new Map());
        setScrollTop(0);
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
  }, [connectionId, displayName, isInvalidDatabase, openNonce, sqlclConnectionName]);

  const canRenderTree = useMemo(() => Boolean(tree && connectionId && sqlclConnectionName), [tree, connectionId, sqlclConnectionName]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }

    const measureViewport = () => {
      setViewportHeight(container.clientHeight || 400);
    };

    measureViewport();
    const resizeObserver =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => measureViewport()) : null;
    resizeObserver?.observe(container);
    window.addEventListener("resize", measureViewport);

    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener("resize", measureViewport);
    };
  }, [canRenderTree]);
  const visibleRows = useMemo(
    () => (tree ? collectVisibleTreeRows(tree, expandedNodeIds, folderFilters, folderVisibleCounts) : []),
    [expandedNodeIds, folderFilters, folderVisibleCounts, tree],
  );
  const visibleNodeIds = useMemo(
    () =>
      visibleRows
        .filter((row): row is VisibleNodeRow => row.kind === "node")
        .map(({ node }) => node.id),
    [visibleRows],
  );
  const visibleNodeIndexMap = useMemo(
    () =>
      new Map(
        visibleRows
          .filter((row): row is VisibleNodeRow => row.kind === "node")
          .map(({ node }, index) => [node.id, index]),
      ),
    [visibleRows],
  );
  const selectedNodes = useMemo(() => {
    return visibleRows
      .filter((row): row is VisibleNodeRow => row.kind === "node" && selectedNodeIds.has(row.node.id))
      .map(({ node }) => node);
  }, [selectedNodeIds, visibleRows]);
  const totalVisibleRows = visibleRows.length;
  const startRowIndex = Math.max(0, Math.floor(scrollTop / TREE_ROW_HEIGHT) - TREE_OVERSCAN_ROWS);
  const endRowIndex = Math.min(
    totalVisibleRows,
    Math.ceil((scrollTop + viewportHeight) / TREE_ROW_HEIGHT) + TREE_OVERSCAN_ROWS,
  );
  const virtualRows = visibleRows.slice(startRowIndex, endRowIndex);
  const topSpacerHeight = startRowIndex * TREE_ROW_HEIGHT;
  const bottomSpacerHeight = Math.max(0, (totalVisibleRows - endRowIndex) * TREE_ROW_HEIGHT);

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
      setFolderVisibleCounts((prev) => {
        const next = new Map(prev);
        next.set(node.id, LARGE_FOLDER_PAGE_SIZE);
        return next;
      });
      setFolderFilters((prev) => {
        if (!prev.has(node.id)) {
          return prev;
        }
        const next = new Map(prev);
        next.delete(node.id);
        return next;
      });
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
      setFolderVisibleCounts((prev) => {
        const next = new Map(prev);
        next.set(node.id, LARGE_FOLDER_PAGE_SIZE);
        return next;
      });
      setFolderFilters((prev) => {
        if (!prev.has(node.id)) {
          return prev;
        }
        const next = new Map(prev);
        next.delete(node.id);
        return next;
      });
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

  async function handleCopy(text: string, label: string, options?: { addAsSnippet?: boolean }) {
    let copied = false;
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        copied = true;
      } else if (legacyCopyText(text)) {
        copied = true;
      } else {
        setManualCopyState({ text, label });
      }
    } catch {
      if (legacyCopyText(text)) {
        copied = true;
      } else {
        setManualCopyState({ text, label });
      }
    } finally {
      setContextMenu(null);
    }
    if (options?.addAsSnippet) {
      addDraftSnippet(text);
      if (!copied) {
        toast.error(`Inserted into the chat input, but clipboard access is unavailable. Copy ${label} manually.`);
      }
      return;
    }
    if (!copied) {
      toast.error(`Clipboard access is unavailable. Copy ${label} manually.`);
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

    const visibleIndex = visibleNodeIndexMap.get(node.id) ?? -1;
    const anchorId = selectionAnchorNodeId ?? node.id;
    const anchorIndex = visibleNodeIndexMap.get(anchorId) ?? -1;

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

  function resolveRefreshTargetNode(targetNode: MetadataTreeNode): MetadataTreeNode | null {
    if (REFRESHABLE_NODE_TYPES.has(targetNode.type)) {
      return targetNode;
    }
    if (!tree || !isSchemaObjectNode(targetNode)) {
      return null;
    }
    const parentNode = findParentNode(tree, targetNode.id);
    if (!parentNode) {
      return null;
    }
    return REFRESHABLE_NODE_TYPES.has(parentNode.type) ? parentNode : null;
  }

  async function fetchNodeDdl(
    node: MetadataTreeNode,
    options?: { forceRefresh?: boolean },
  ) {
    if (!connectionId || !sqlclConnectionName) {
      return null;
    }
    const schemaName =
      typeof node.metadata?.schemaName === "string" ? node.metadata.schemaName.trim() : "";
    const objectName =
      typeof node.metadata?.objectName === "string" ? node.metadata.objectName.trim() : node.label.trim();
    if (!schemaName || !objectName) {
      toast.error(`Missing schema or object name for ${node.label}`);
      setContextMenu(null);
      return null;
    }

    setLoadingNodeIds((prev) => new Set(prev).add(node.id));
    try {
      return isTableNode(node)
        ? await fetchTableDdl({
            connectionId,
            sqlclConnectionName,
            schemaName,
            tableName: objectName,
            forceRefresh: options?.forceRefresh ?? false,
          })
        : await fetchSourceDdl({
            connectionId,
            sqlclConnectionName,
            schemaName,
            objectType: node.type,
            objectName,
            forceRefresh: options?.forceRefresh ?? false,
          });
    } catch (nextError) {
      toast.error(getErrorMessage(nextError, `Failed to load DDL for ${objectName}`));
      return null;
    } finally {
      setLoadingNodeIds((prev) => {
        const next = new Set(prev);
        next.delete(node.id);
        return next;
      });
    }
  }

  async function handleNodeDdl(
    node: MetadataTreeNode,
    options?: { forceRefresh?: boolean; insertPrompt?: boolean },
  ) {
    const response = await fetchNodeDdl(node, options);
    if (!response) {
      setContextMenu(null);
      return;
    }
    const schemaName =
      typeof node.metadata?.schemaName === "string" ? node.metadata.schemaName.trim() : "";
    const objectName =
      typeof node.metadata?.objectName === "string" ? node.metadata.objectName.trim() : node.label.trim();
    if (options?.insertPrompt) {
      addDraftSnippet(formatObjectDdlPrompt(node, response.sqlText, sqlclConnectionName, displayName));
      toast.success(
        response.cacheHit
          ? `Inserted cached DDL for ${schemaName}.${objectName}`
          : `Fetched and inserted DDL for ${schemaName}.${objectName}`,
      );
    } else {
      toast.success(`Refreshed DDL for ${schemaName}.${objectName}`);
    }
    setContextMenu(null);
  }

  async function handleViewNodeDdl(node: MetadataTreeNode) {
    const response = await fetchNodeDdl(node);
    if (!response) {
      setContextMenu(null);
      return;
    }
    setObjectViewDialog({
      node,
      sqlText: response.sqlText,
    });
    if (response.cacheHit) {
      toast.success(`Opened cached DDL for ${node.label}`);
    } else {
      toast.success(`Fetched and opened DDL for ${node.label}`);
    }
    setContextMenu(null);
  }

  async function handleRefreshViewDialog() {
    if (!objectViewDialog) {
      return;
    }
    const response = await fetchNodeDdl(objectViewDialog.node, { forceRefresh: true });
    if (!response) {
      return;
    }
    setObjectViewDialog((prev) =>
      prev
        ? {
            ...prev,
            sqlText: response.sqlText,
          }
        : prev,
    );
    toast.success(`Refreshed DDL for ${objectViewDialog.node.label}`);
    sourceSelectionTextRef.current = "";
    setSelectedSourceText("");
  }

  function handleAddSelectedCodeToPrompt() {
    const selectedText = sourceSelectionTextRef.current.trim();
    if (!objectViewDialog || !selectedText) {
      return;
    }
    addDraftSnippet(
      hasInsertedSelectionContext
        ? formatSelectedCodeOnly(selectedText)
        : formatSelectedCodePrompt(objectViewDialog.node, selectedText, sqlclConnectionName, displayName),
    );
    setHasInsertedSelectionContext(true);
    toast.success(t("chat.sourceSelectionAddedToPrompt"));
  }

  function updateSourceSelectionText() {
    const nextText = getSelectedTextWithinContainer(sourceSelectionContainerRef.current);
    sourceSelectionTextRef.current = nextText;
    setSelectedSourceText(nextText);
  }

  function renderFolderControlsRow({
    node,
    depth,
    totalChildren,
    filteredChildren,
    visibleChildren,
    filterText,
    hasMore,
  }: VisibleFolderControlsRow) {
    const showingSummary =
      filteredChildren === totalChildren
        ? `Showing ${visibleChildren} / ${totalChildren}`
        : `Showing ${visibleChildren} / ${filteredChildren} matches`;

    return (
      <div key={`${node.id}:controls`} className="min-w-max">
        <div
          className="flex min-w-max items-center gap-2 rounded-md px-1.5 py-1"
          style={{ paddingLeft: `${depth * 14 + 4}px`, minHeight: `${TREE_ROW_HEIGHT}px` }}
          onClick={(event) => event.stopPropagation()}
        >
          <input
            type="text"
            value={filterText}
            onChange={(event) => {
              const nextValue = event.target.value;
              setFolderFilters((prev) => {
                const next = new Map(prev);
                if (nextValue.trim()) {
                  next.set(node.id, nextValue);
                } else {
                  next.delete(node.id);
                }
                return next;
              });
              setFolderVisibleCounts((prev) => {
                const next = new Map(prev);
                next.set(node.id, LARGE_FOLDER_PAGE_SIZE);
                return next;
              });
            }}
            placeholder={`Filter ${node.label}`}
            className="h-7 min-w-[220px] flex-1 rounded-md border bg-background px-2 text-[12px] outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring"
          />
          <span className="shrink-0 text-[11px] text-muted-foreground">{showingSummary}</span>
          {hasMore ? (
            <button
              type="button"
              onClick={() =>
                setFolderVisibleCounts((prev) => {
                  const next = new Map(prev);
                  next.set(node.id, visibleChildren + LARGE_FOLDER_PAGE_SIZE);
                  return next;
                })
              }
              className="shrink-0 rounded-md border px-2 py-1 text-[11px] transition-colors hover:bg-muted"
            >
              Load More
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  function renderNodeRow({ node, depth }: VisibleNodeRow) {
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
          style={{ paddingLeft: `${depth * 14 + 4}px`, minHeight: `${TREE_ROW_HEIGHT}px` }}
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
      </div>
    );
  }

  function renderRow(row: VisibleTreeRow) {
    if (row.kind === "folder-controls") {
      return renderFolderControlsRow(row);
    }
    return renderNodeRow(row);
  }

  const contextRefreshTarget = contextMenu ? resolveRefreshTargetNode(contextMenu.node) : null;
  const contextTableNode = contextMenu ? isTableNode(contextMenu.node) : false;
  const contextSourceDdlNode = contextMenu ? isSourceDdlNode(contextMenu.node) : false;
  const contextNodeDdlEnabled = contextTableNode || contextSourceDdlNode;
  const contextCanCopyNodePath = contextMenu ? canCopyNodePath(contextMenu.node) : false;

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
        <div
          ref={scrollContainerRef}
          className="min-h-0 flex-1 overflow-auto px-2 py-2"
          onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        >
          <div className="min-w-max">
            {topSpacerHeight > 0 ? <div style={{ height: `${topSpacerHeight}px` }} /> : null}
            {virtualRows.map((row) => renderRow(row))}
            {bottomSpacerHeight > 0 ? <div style={{ height: `${bottomSpacerHeight}px` }} /> : null}
          </div>
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
          {isSelectAiProfileNode(contextMenu.node) ? (
            <button
              type="button"
              onClick={() =>
                void handleCopy(formatSelectAiProfilePrompt(contextMenu.node, sqlclConnectionName), "selectai profile", {
                  addAsSnippet: true,
                })
              }
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
            >
              <span>{t("chat.setSelectAiProfile")}</span>
            </button>
          ) : null}
          <button
            type="button"
            disabled={!contextRefreshTarget && !contextNodeDdlEnabled}
            onClick={() => {
              if (contextNodeDdlEnabled) {
                void handleNodeDdl(contextMenu.node, { forceRefresh: true });
                return;
              }
              if (!contextRefreshTarget) {
                return;
              }
              void handleRefreshNode(contextRefreshTarget);
            }}
            className={cn(
              "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent",
              !contextRefreshTarget && !contextNodeDdlEnabled && "cursor-not-allowed opacity-50 hover:bg-transparent",
            )}
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
          {contextNodeDdlEnabled ? (
            <button
              type="button"
              onClick={() => void handleViewNodeDdl(contextMenu.node)}
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
            >
              <Eye className="h-4 w-4" />
              <span>VIEW</span>
            </button>
          ) : null}
          {contextNodeDdlEnabled ? (
            <button
              type="button"
              onClick={() => void handleNodeDdl(contextMenu.node, { insertPrompt: true })}
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
            >
              <FileCode className="h-4 w-4" />
              <span>Quick DDL</span>
            </button>
          ) : null}
          {isSqlCopyNode(contextMenu.node) ? (
            <button
              type="button"
              onClick={() =>
                void handleCopy(formatDiagnosisSqlForCopy(contextMenu.node, sqlclConnectionName), "sql", {
                  addAsSnippet: contextMenu.node.type === "useful_diagnosis",
                })
              }
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
            >
              <span>Copy SQL</span>
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={() =>
                  void handleCopy(
                    formatNodeNamePromptForCopy(contextMenu.node, sqlclConnectionName, displayName),
                    "name prompt",
                    { addAsSnippet: true },
                  )
                }
                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
              >
                <span>Copy Name</span>
              </button>
              {contextCanCopyNodePath ? (
                <button
                  type="button"
                  onClick={() =>
                    void handleCopy(
                      formatNodePathsForCopy(resolveNodesForCopy(contextMenu.node), sqlclConnectionName, displayName),
                      selectedNodeIds.has(contextMenu.node.id) && selectedNodes.length > 1 ? "node paths" : "node path",
                      { addAsSnippet: true },
                    )
                  }
                  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
                >
                  <span>
                    {isSelectAiProfileNode(contextMenu.node)
                      ? t("chat.checkSelectAiConfig")
                      : selectedNodeIds.has(contextMenu.node.id) && selectedNodes.length > 1
                        ? "Copy Node Paths"
                        : "Copy Node Path"}
                  </span>
                </button>
              ) : null}
            </>
          )}
        </div>
      ) : null}

      <Dialog
        open={Boolean(objectViewDialog)}
        onOpenChange={(open) => {
          if (!open) {
            setObjectViewDialog(null);
            sourceSelectionTextRef.current = "";
            setSelectedSourceText("");
            setHasInsertedSelectionContext(false);
          }
        }}
      >
        <DialogContent className="flex h-[88vh] w-[92vw] max-w-[1200px] flex-col gap-0 overflow-hidden rounded-2xl p-0">
          <div className="border-b px-5 py-3 pr-16">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <DialogTitle className="text-sm font-semibold">
                  {objectViewDialog ? `${objectViewDialog.node.label} Source / DDL` : "Object Source / DDL"}
                </DialogTitle>
                {objectViewDialog ? (
                  <div className="mt-1 text-xs text-muted-foreground">
                    {getRelativeNodePath(objectViewDialog.node, displayName)}
                  </div>
                ) : null}
              </div>
              {objectViewDialog ? (
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    onClick={handleAddSelectedCodeToPrompt}
                    disabled={!selectedSourceText.trim()}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-colors hover:bg-muted",
                      !selectedSourceText.trim() && "cursor-not-allowed opacity-50 hover:bg-transparent",
                    )}
                  >
                    <FileCode className="h-3.5 w-3.5" />
                    <span>{t("chat.addSelectionToPrompt")}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleCopy(objectViewDialog.sqlText, "sql")}
                    className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-colors hover:bg-muted"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy SQL</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleRefreshViewDialog()}
                    disabled={loadingNodeIds.has(objectViewDialog.node.id)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-colors hover:bg-muted",
                      loadingNodeIds.has(objectViewDialog.node.id) && "cursor-not-allowed opacity-60 hover:bg-transparent",
                    )}
                  >
                    {loadingNodeIds.has(objectViewDialog.node.id) ? (
                      <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3.5 w-3.5" />
                    )}
                    <span>Refresh</span>
                  </button>
                </div>
              ) : null}
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
            {objectViewDialog ? (
              <div
                ref={sourceSelectionContainerRef}
                className="overflow-hidden rounded-lg border bg-muted/20"
                onMouseUp={updateSourceSelectionText}
                onKeyUp={updateSourceSelectionText}
              >
                <div className="max-h-full overflow-auto">
                  <div className="min-w-max font-mono text-xs leading-6">
                    {normalizeCodeLines(objectViewDialog.sqlText).map((line, index) => (
                      <div
                        key={`${objectViewDialog.node.id}-${index + 1}`}
                        className="grid grid-cols-[auto,1fr] border-b border-border/40 last:border-b-0"
                      >
                        <div className="select-none border-r bg-muted/40 px-3 py-0.5 text-right text-muted-foreground">
                          {index + 1}
                        </div>
                        <pre className="overflow-x-visible px-3 py-0.5 whitespace-pre-wrap break-words text-foreground">
                          {line || " "}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </DialogContent>
      </Dialog>

      {manualCopyState ? (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 px-4 backdrop-blur-sm">
          <div className="flex w-full max-w-2xl flex-col gap-3 rounded-lg border bg-background p-4 shadow-lg">
            <div>
              <div className="text-sm font-semibold">Manual Copy</div>
              <p className="mt-1 text-xs text-muted-foreground">
                Automatic clipboard access is unavailable in this browser. Copy the {manualCopyState.label} manually.
              </p>
            </div>
            <textarea
              ref={manualCopyTextareaRef}
              readOnly
              value={manualCopyState.text}
              className="min-h-40 w-full rounded-md border bg-background px-3 py-2 font-mono text-xs outline-none"
            />
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted-foreground">Text is selected automatically. Press Ctrl+C to copy.</span>
              <button
                type="button"
                onClick={() => setManualCopyState(null)}
                className="rounded-md border px-3 py-1.5 text-xs transition-colors hover:bg-muted"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
