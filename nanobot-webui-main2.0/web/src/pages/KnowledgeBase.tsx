import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { AlertCircle, CheckCircle2, Database, FileText, Loader2, Search, Trash2, Upload } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  useDeleteKnowledgeDocument,
  useKnowledgeBaseDocuments,
  useKnowledgeBaseHealth,
  useSearchKnowledgeBase,
  useUploadKnowledgeDocument,
  type KnowledgeBaseEngine,
  type KnowledgeBaseUploadResult,
} from "../hooks/useKnowledgeBase";

const TOP_K_OPTIONS = ["5", "10", "20", "50"] as const;
const SCORE_OPTIONS = ["0.300", "0.500", "0.700", "0.900"] as const;
const DOCUMENT_TYPE_OPTIONS = ["all", "pdf", "txt"] as const;
const PAGE_SIZE_OPTIONS = ["10", "20", "50"] as const;
const DEVICE_OPTIONS = ["auto", "cuda", "cpu"] as const;
const ENGINE_OPTIONS = ["qwen", "bge"] as const;
const ENGINE_STORAGE_KEY = "knowledgeBase.selectedEngine";

const ENGINE_TABLES: Record<KnowledgeBaseEngine, { docs: string; chunks: string }> = {
  qwen: {
    docs: "LC_DEMO_DOCUMENTS",
    chunks: "LC_DEMO_CHUNKS",
  },
  bge: {
    docs: "LC_DEMO_DOCUMENTS_BGE",
    chunks: "LC_DEMO_CHUNKS_BGE",
  },
};

interface EngineSearchState {
  searchInput: string;
  topK: (typeof TOP_K_OPTIONS)[number];
  score: (typeof SCORE_OPTIONS)[number];
  documentType: (typeof DOCUMENT_TYPE_OPTIONS)[number];
  device: (typeof DEVICE_OPTIONS)[number];
  sourceFile: string;
  hasSearched: boolean;
  results: Array<{ title: string; score: number }>;
}

interface EngineListState {
  listInput: string;
  listKeyword: string;
  listDocumentType: (typeof DOCUMENT_TYPE_OPTIONS)[number];
  pageSize: (typeof PAGE_SIZE_OPTIONS)[number];
  page: number;
}

const DEFAULT_ENGINE_SEARCH_STATE: EngineSearchState = {
  searchInput: "",
  topK: "10",
  score: "0.300",
  documentType: "all",
  device: "auto",
  sourceFile: "webui",
  hasSearched: false,
  results: [],
};

const DEFAULT_ENGINE_LIST_STATE: EngineListState = {
  listInput: "",
  listKeyword: "",
  listDocumentType: "all",
  pageSize: "10",
  page: 1,
};

function inferDocumentType(name: string): "pdf" | "txt" | undefined {
  const lowered = name.toLowerCase();
  if (lowered.endsWith(".pdf")) {
    return "pdf";
  }
  if (lowered.endsWith(".txt")) {
    return "txt";
  }
  return undefined;
}

function getSelectedFileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function mergeSelectedFiles(existingFiles: File[], incomingFiles: File[]): File[] {
  const merged = [...existingFiles];
  const seen = new Set(existingFiles.map(getSelectedFileKey));

  for (const file of incomingFiles) {
    const fileKey = getSelectedFileKey(file);
    if (!seen.has(fileKey)) {
      seen.add(fileKey);
      merged.push(file);
    }
  }

  return merged;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export default function KnowledgeBase() {
  const { t } = useTranslation();
  const [engine, setEngine] = useState<KnowledgeBaseEngine>(() => {
    if (typeof window === "undefined") {
      return "qwen";
    }
    const savedEngine = window.localStorage.getItem(ENGINE_STORAGE_KEY);
    return savedEngine === "bge" ? "bge" : "qwen";
  });
  const healthQuery = useKnowledgeBaseHealth(engine);
  const uploadMutation = useUploadKnowledgeDocument();
  const searchMutation = useSearchKnowledgeBase();
  const deleteMutation = useDeleteKnowledgeDocument();
  const [searchStates, setSearchStates] = useState<Record<KnowledgeBaseEngine, EngineSearchState>>({
    qwen: { ...DEFAULT_ENGINE_SEARCH_STATE },
    bge: { ...DEFAULT_ENGINE_SEARCH_STATE },
  });
  const [listStates, setListStates] = useState<Record<KnowledgeBaseEngine, EngineListState>>({
    qwen: { ...DEFAULT_ENGINE_LIST_STATE },
    bge: { ...DEFAULT_ENGINE_LIST_STATE },
  });
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadResultsByEngine, setUploadResultsByEngine] = useState<
    Record<KnowledgeBaseEngine, KnowledgeBaseUploadResult[]>
  >({
    qwen: [],
    bge: [],
  });
  const [fileInputKey, setFileInputKey] = useState(0);

  const searchState = searchStates[engine];
  const listState = listStates[engine];
  const { searchInput, topK, score, documentType, device, sourceFile, hasSearched } = searchState;
  const { listInput, listKeyword, listDocumentType, pageSize, page } = listState;

  const updateSearchState = (patch: Partial<EngineSearchState>) => {
    setSearchStates((current) => ({
      ...current,
      [engine]: {
        ...current[engine],
        ...patch,
      },
    }));
  };

  const updateListState = (patch: Partial<EngineListState>) => {
    setListStates((current) => ({
      ...current,
      [engine]: {
        ...current[engine],
        ...patch,
      },
    }));
  };

  const documentListQuery = useKnowledgeBaseDocuments({
    engine,
    page,
    pageSize: Number(pageSize),
    keyword: listKeyword.trim() || undefined,
    documentType: listDocumentType === "all" ? undefined : listDocumentType,
  });

  const searchResults = hasSearched ? searchState.results : [];
  const healthOk = healthQuery.data?.status === "ok";
  const activeTables = ENGINE_TABLES[engine];
  const uploadResults = uploadResultsByEngine[engine];
  const documentItems = documentListQuery.data?.items ?? [];
  const totalDocuments = documentListQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalDocuments / Number(pageSize)));
  const totalSelectedBytes = selectedFiles.reduce((sum, file) => sum + file.size, 0);

  useEffect(() => {
    window.localStorage.setItem(ENGINE_STORAGE_KEY, engine);
  }, [engine]);

  async function handleDeleteDocument(docId: number, documentName: string): Promise<void> {
    const confirmed = window.confirm(
      t("knowledgeBase.messages.confirmDelete", { name: documentName }),
    );
    if (!confirmed) {
      return;
    }
    await deleteMutation.mutateAsync({ docId, engine });
    if (documentItems.length === 1 && page > 1) {
      updateListState({ page: Math.max(1, page - 1) });
    }
  }

  async function handleUpload(): Promise<void> {
    if (selectedFiles.length === 0) {
      toast.error(t("knowledgeBase.messages.selectFilesFirst"));
      return;
    }

    let successCount = 0;
    let insertedCount = 0;
    let duplicateCount = 0;
    let failedCount = 0;
    const latestResults: KnowledgeBaseUploadResult[] = [];

    for (const file of selectedFiles) {
      try {
        const result = await uploadMutation.mutateAsync({
          file,
          engine,
          documentType: inferDocumentType(file.name),
          sourceFile,
          device,
        });
        latestResults.push(result);
        successCount += 1;
        if (result.inserted) {
          insertedCount += 1;
        } else {
          duplicateCount += 1;
        }
      } catch {
        failedCount += 1;
      }
    }

    if (latestResults.length > 0) {
      setUploadResultsByEngine((current) => ({
        ...current,
        [engine]: [...latestResults, ...current[engine]].slice(0, 10),
      }));
    }

    if (successCount > 0) {
      toast.success(
        t("knowledgeBase.messages.uploadSuccess", {
          count: successCount,
          inserted: insertedCount,
          duplicates: duplicateCount,
        }),
      );
      setSelectedFiles([]);
      setFileInputKey((current) => current + 1);
    }

    if (failedCount > 0) {
      toast.error(t("knowledgeBase.messages.uploadPartialFailed", { count: failedCount }));
    }
  }

  async function handleSearch(): Promise<void> {
    const prompt = searchInput.trim();
    if (!prompt) {
      toast.error(t("knowledgeBase.messages.searchPromptRequired"));
      return;
    }

    const results = await searchMutation.mutateAsync({
      prompt,
      engine,
      topK: Number(topK),
      rerankerScore: Number(score),
      documentType: documentType === "all" ? undefined : documentType,
      device,
    });
    updateSearchState({ hasSearched: true, results });
  }

  function handleApplyListFilters(): void {
    updateListState({
      page: 1,
      listKeyword: listInput,
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("knowledgeBase.title")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("knowledgeBase.subtitle")}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={healthOk ? "secondary" : "destructive"} className="w-fit">
            {healthQuery.isLoading
              ? t("knowledgeBase.statusChecking")
              : healthOk
                ? t("knowledgeBase.statusConnected")
                : t("knowledgeBase.statusDisconnected")}
          </Badge>
          <Badge variant="outline" className="w-fit">
            {t("knowledgeBase.badge")}
          </Badge>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
        <div className="space-y-6">
          <Card className="border-primary/10 shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="h-4 w-4 text-primary" />
                {t("knowledgeBase.ingestTitle")}
              </CardTitle>
              <CardDescription>
                {t("knowledgeBase.ingestDescription")}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>{t("knowledgeBase.engineLabel")}</Label>
                  <Select
                    value={engine}
                    onValueChange={(value) => {
                      setEngine(value as KnowledgeBaseEngine);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t("knowledgeBase.engineLabel")} />
                    </SelectTrigger>
                    <SelectContent>
                      {ENGINE_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {t(`knowledgeBase.engines.${option}`)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="rounded-lg border bg-muted/30 p-3 text-sm">
                  <p className="font-medium text-foreground">{t("knowledgeBase.tableBindingTitle")}</p>
                  <p className="mt-1 text-muted-foreground">{activeTables.docs}</p>
                  <p className="text-muted-foreground">{activeTables.chunks}</p>
                </div>
              </div>

              <div className="rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
                <div className="flex items-center justify-between gap-3">
                  <span>{t("knowledgeBase.apiEndpoint")}</span>
                  <span className="truncate font-mono">{healthQuery.data?.baseUrl ?? "http://127.0.0.1:19000"}</span>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>{t("knowledgeBase.deviceLabel")}</Label>
                  <Select value={device} onValueChange={(value) => updateSearchState({ device: value as (typeof DEVICE_OPTIONS)[number] })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t("knowledgeBase.deviceLabel")} />
                    </SelectTrigger>
                    <SelectContent>
                      {DEVICE_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {t(`knowledgeBase.devices.${option}`)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="kb-source-file">{t("knowledgeBase.sourceFileLabel")}</Label>
                  <Input
                    id="kb-source-file"
                    value={sourceFile}
                    onChange={(event) => updateSearchState({ sourceFile: event.target.value })}
                    placeholder={t("knowledgeBase.sourceFilePlaceholder")}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="kb-upload">{t("knowledgeBase.uploadLabel")}</Label>
                <Input
                  key={fileInputKey}
                  id="kb-upload"
                  type="file"
                  multiple
                  accept=".txt,.pdf"
                  onChange={(event) => {
                    const files = Array.from(event.target.files ?? []);
                    const validFiles = files.filter((file) => inferDocumentType(file.name));
                    if (validFiles.length !== files.length) {
                      toast.error(t("knowledgeBase.messages.invalidFileType"));
                    }
                    setSelectedFiles((current) => mergeSelectedFiles(current, validFiles));
                    event.target.value = "";
                  }}
                />
                <p className="text-xs text-muted-foreground">{t("knowledgeBase.supportedTypes")}</p>
              </div>

              {selectedFiles.length > 0 ? (
                <div className="rounded-lg border bg-muted/30 p-3">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">{t("knowledgeBase.pendingFiles")}</p>
                      <p className="text-xs text-muted-foreground">
                        {`共 ${selectedFiles.length} 个文件，合计 ${formatFileSize(totalSelectedBytes)}`}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={uploadMutation.isPending}
                      onClick={() => setSelectedFiles([])}
                    >
                      清空全部
                    </Button>
                  </div>
                  <div className="space-y-1.5">
                    {selectedFiles.map((file) => (
                      <div
                        key={getSelectedFileKey(file)}
                        className="flex items-center gap-2 text-sm"
                      >
                        <FileText className="h-3.5 w-3.5 text-primary" />
                        <span className="min-w-0 flex-1 truncate">{file.name}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          title={t("common.delete")}
                          disabled={uploadMutation.isPending}
                          onClick={() => {
                            setSelectedFiles((current) =>
                              current.filter(
                                (currentFile) => getSelectedFileKey(currentFile) !== getSelectedFileKey(file),
                              ),
                            );
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border border-dashed px-3 py-4 text-sm text-muted-foreground">
                  {t("knowledgeBase.uploadEmpty")}
                </div>
              )}

              <Button
                className="w-full sm:w-auto"
                onClick={() => void handleUpload()}
                disabled={selectedFiles.length === 0 || uploadMutation.isPending}
              >
                {uploadMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                {t("knowledgeBase.uploadButton")}
              </Button>
            </CardContent>
          </Card>

          <Card className="border-primary/10 shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-base">
                <Search className="h-4 w-4 text-primary" />
                {t("knowledgeBase.searchTitle")}
              </CardTitle>
              <CardDescription>
                {t("knowledgeBase.searchDescription")}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>{t("knowledgeBase.searchLabel")}</Label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Input
                    value={searchInput}
                    onChange={(event) => updateSearchState({ searchInput: event.target.value })}
                    placeholder={t("knowledgeBase.searchPlaceholder")}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void handleSearch();
                      }
                    }}
                  />
                  <Button
                    type="button"
                    className="sm:min-w-[96px]"
                    onClick={() => void handleSearch()}
                    disabled={searchMutation.isPending}
                  >
                    {searchMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : null}
                    {t("knowledgeBase.searchButton")}
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>{t("knowledgeBase.topKLabel")}</Label>
                  <Select value={topK} onValueChange={(value) => updateSearchState({ topK: value as (typeof TOP_K_OPTIONS)[number] })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t("knowledgeBase.topKLabel")} />
                    </SelectTrigger>
                    <SelectContent>
                      {TOP_K_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>{t("knowledgeBase.scoreLabel")}</Label>
                  <Select value={score} onValueChange={(value) => updateSearchState({ score: value as (typeof SCORE_OPTIONS)[number] })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t("knowledgeBase.scoreLabel")} />
                    </SelectTrigger>
                    <SelectContent>
                      {SCORE_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>{t("knowledgeBase.documentTypeLabel")}</Label>
                  <Select
                    value={documentType}
                    onValueChange={(value) => updateSearchState({ documentType: value as (typeof DOCUMENT_TYPE_OPTIONS)[number] })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t("knowledgeBase.documentTypeLabel")} />
                    </SelectTrigger>
                    <SelectContent>
                      {DOCUMENT_TYPE_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {t(`knowledgeBase.documentTypes.${option}`)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="rounded-lg border bg-muted/30 p-3 text-sm">
                  <p className="font-medium text-foreground">{t("knowledgeBase.currentModeTitle")}</p>
                  <p className="mt-1 text-muted-foreground">{t("knowledgeBase.currentModeValue")}</p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">{t("knowledgeBase.engineBadge", { engine: t(`knowledgeBase.engines.${engine}`) })}</Badge>
                <Badge variant="outline">{t("knowledgeBase.documentTypeBadge", { type: t(`knowledgeBase.documentTypes.${documentType}`) })}</Badge>
                <Badge variant="outline">{t("knowledgeBase.resultCount", { count: searchResults.length })}</Badge>
                <Badge variant="outline">TopK {topK}</Badge>
                <Badge variant="outline">Score &gt;= {score}</Badge>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="border-primary/10 shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-base">{t("knowledgeBase.resultTitle")}</CardTitle>
            <CardDescription>
              {t("knowledgeBase.resultDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border bg-muted/30 p-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  {healthOk ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-destructive" />
                  )}
                  {t("knowledgeBase.healthTitle")}
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {healthQuery.isLoading
                    ? t("knowledgeBase.statusChecking")
                    : healthOk
                      ? t("knowledgeBase.healthHealthy")
                      : healthQuery.error
                        ? t("knowledgeBase.healthUnavailable")
                        : t("knowledgeBase.statusDisconnected")}
                </p>
              </div>

              <div className="rounded-lg border bg-muted/30 p-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Upload className="h-4 w-4 text-primary" />
                  {t("knowledgeBase.uploadResultsTitle")}
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {uploadResults.length > 0
                    ? t("knowledgeBase.uploadResultsCount", { count: uploadResults.length })
                    : t("knowledgeBase.uploadEmpty")}
                </p>
              </div>
            </div>

            <div className="rounded-xl border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("knowledgeBase.table.title")}</TableHead>
                    <TableHead className="w-32 whitespace-nowrap">{t("knowledgeBase.table.rerankScore")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {searchResults.map((doc, index) => (
                    <TableRow key={`${doc.title}-${doc.score}-${index}`}>
                      <TableCell>
                        <div className="line-clamp-2 font-medium leading-5">{doc.title}</div>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-sm font-medium text-primary">{doc.score.toFixed(3)}</span>
                      </TableCell>
                    </TableRow>
                  ))}
                  {searchMutation.isPending && (
                    <TableRow>
                      <TableCell colSpan={2} className="py-12 text-center text-sm text-muted-foreground">
                        <div className="flex items-center justify-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {t("knowledgeBase.messages.searching")}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  {!searchMutation.isPending && hasSearched && searchResults.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={2} className="py-12 text-center text-sm text-muted-foreground">
                        {t("knowledgeBase.noResults")}
                      </TableCell>
                    </TableRow>
                  )}
                  {!searchMutation.isPending && !hasSearched && (
                    <TableRow>
                      <TableCell colSpan={2} className="py-12 text-center text-sm text-muted-foreground">
                        {t("knowledgeBase.searchEmpty")}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>

            {uploadResults.length > 0 && (
              <div className="rounded-xl border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("knowledgeBase.uploadTable.title")}</TableHead>
                      <TableHead className="w-28">{t("knowledgeBase.uploadTable.status")}</TableHead>
                      <TableHead className="w-28">{t("knowledgeBase.uploadTable.chunks")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {uploadResults.map((item) => (
                      <TableRow key={`${item.documentName}-${item.docId ?? "na"}-${item.insertedChunkCount}`}>
                        <TableCell>
                          <div className="space-y-1">
                            <div className="line-clamp-2 font-medium leading-5">{item.documentName}</div>
                            <div className="text-xs text-muted-foreground">
                              {t("knowledgeBase.uploadTable.length", { count: item.fullTextLength })}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={item.inserted ? "secondary" : "outline"}>
                            {item.inserted ? t("knowledgeBase.uploadStatus.inserted") : t("knowledgeBase.uploadStatus.duplicate")}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-sm text-muted-foreground">
                          {item.insertedChunkCount}/{item.parsedChunkCount}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            <div className="rounded-xl border">
              <div className="flex flex-col gap-3 border-b p-4">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-sm font-medium">{t("knowledgeBase.documentListTitle")}</p>
                    <p className="text-sm text-muted-foreground">{t("knowledgeBase.documentListDescription")}</p>
                  </div>
                  <Badge variant="outline">{t("knowledgeBase.documentTotal", { count: totalDocuments })}</Badge>
                </div>

                <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_120px]">
                  <div className="flex gap-2">
                    <Input
                      value={listInput}
                      onChange={(event) => updateListState({ listInput: event.target.value })}
                      placeholder={t("knowledgeBase.documentListSearchPlaceholder")}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          handleApplyListFilters();
                        }
                      }}
                    />
                    <Button type="button" variant="outline" onClick={handleApplyListFilters}>
                      {t("knowledgeBase.filterButton")}
                    </Button>
                  </div>

                  <Select
                    value={listDocumentType}
                    onValueChange={(value) => {
                      updateListState({
                        listDocumentType: value as (typeof DOCUMENT_TYPE_OPTIONS)[number],
                        page: 1,
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t("knowledgeBase.documentTypeLabel")} />
                    </SelectTrigger>
                    <SelectContent>
                      {DOCUMENT_TYPE_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {t(`knowledgeBase.documentTypes.${option}`)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Select
                    value={pageSize}
                    onValueChange={(value) => {
                      updateListState({
                        pageSize: value as (typeof PAGE_SIZE_OPTIONS)[number],
                        page: 1,
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t("knowledgeBase.pageSizeLabel")} />
                    </SelectTrigger>
                    <SelectContent>
                      {PAGE_SIZE_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {t("knowledgeBase.pageSizeOption", { count: Number(option) })}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("knowledgeBase.documentsTable.title")}</TableHead>
                    <TableHead className="w-24">{t("knowledgeBase.documentsTable.type")}</TableHead>
                    <TableHead className="w-28">{t("knowledgeBase.documentsTable.chunks")}</TableHead>
                    <TableHead className="w-40">{t("knowledgeBase.documentsTable.createdAt")}</TableHead>
                    <TableHead className="w-24 text-right">{t("knowledgeBase.documentsTable.actions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documentListQuery.isLoading && (
                    <TableRow>
                      <TableCell colSpan={5} className="py-12 text-center text-sm text-muted-foreground">
                        <div className="flex items-center justify-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {t("knowledgeBase.messages.loadingDocuments")}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}

                  {!documentListQuery.isLoading && documentItems.map((item) => (
                    <TableRow key={item.docId}>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="line-clamp-2 font-medium leading-5">{item.documentName}</div>
                          <div className="text-xs text-muted-foreground">
                            {item.sourceFile || t("common.noData")}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="uppercase text-muted-foreground">{item.documentType}</TableCell>
                      <TableCell className="font-mono text-muted-foreground">{item.chunkCount}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{item.createdAt ?? "-"}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="icon"
                          disabled={deleteMutation.isPending}
                          title={t("knowledgeBase.deleteDocument")}
                          onClick={() => void handleDeleteDocument(item.docId, item.documentName)}
                        >
                          {deleteMutation.isPending && deleteMutation.variables?.docId === item.docId ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4 text-destructive" />
                          )}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}

                  {!documentListQuery.isLoading && documentItems.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="py-12 text-center text-sm text-muted-foreground">
                        {t("knowledgeBase.documentListEmpty")}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>

              <div className="flex flex-col gap-3 border-t p-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-muted-foreground">
                  {t("knowledgeBase.paginationSummary", {
                    page,
                    totalPages,
                    total: totalDocuments,
                  })}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={page <= 1 || documentListQuery.isFetching}
                    onClick={() => updateListState({ page: Math.max(1, page - 1) })}
                  >
                    {t("knowledgeBase.prevPage")}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={page >= totalPages || documentListQuery.isFetching}
                    onClick={() => updateListState({ page: Math.min(totalPages, page + 1) })}
                  >
                    {t("knowledgeBase.nextPage")}
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
