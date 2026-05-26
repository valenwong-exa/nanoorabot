import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Bot, FileText, Save } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { Textarea } from "../components/ui/textarea";
import { useAgentSettings, useSaveWorkspaceFile, useWorkspaceFile } from "../hooks/useConfig";
import api from "../lib/api";

export default function Soul() {
  const { t } = useTranslation();
  const { data: agentSettings } = useAgentSettings();
  const { data, isLoading } = useWorkspaceFile("SOUL.md");
  const saveWorkspaceFile = useSaveWorkspaceFile();
  const [content, setContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [portraitSrc, setPortraitSrc] = useState("/SOUL.png");
  const portraitBlobUrlRef = useRef<string | null>(null);

  const workspaceSoulImagePath = useMemo(() => {
    if (!agentSettings?.workspace) {
      return null;
    }
    return `${agentSettings.workspace}\\SOUL.png`;
  }, [agentSettings?.workspace]);

  useEffect(() => {
    if (typeof data?.content === "string") {
      setContent(data.content);
      setDirty(false);
    }
  }, [data?.content]);

  useEffect(() => {
    let active = true;

    const cleanupBlobUrl = () => {
      if (portraitBlobUrlRef.current) {
        URL.revokeObjectURL(portraitBlobUrlRef.current);
        portraitBlobUrlRef.current = null;
      }
    };

    const loadWorkspacePortrait = async () => {
      if (!workspaceSoulImagePath) {
        cleanupBlobUrl();
        setPortraitSrc("/SOUL.png");
        return;
      }

      try {
        const resp = await api.get<Blob>("/workspace/file", {
          params: { path: workspaceSoulImagePath },
          responseType: "blob",
        });

        if (!active) {
          return;
        }

        cleanupBlobUrl();
        const nextBlobUrl = URL.createObjectURL(resp.data);
        portraitBlobUrlRef.current = nextBlobUrl;
        setPortraitSrc(nextBlobUrl);
      } catch {
        cleanupBlobUrl();
        if (active) {
          setPortraitSrc("/SOUL.png");
        }
      }
    };

    void loadWorkspacePortrait();

    return () => {
      active = false;
      cleanupBlobUrl();
    };
  }, [workspaceSoulImagePath]);

  const lineCount = useMemo(() => {
    if (!content) {
      return 0;
    }
    return content.split(/\r?\n/).length;
  }, [content]);

  const handleSave = () => {
    saveWorkspaceFile.mutate(
      { name: "SOUL.md", content },
      {
        onSuccess: () => setDirty(false),
      },
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("soul.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("soul.subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">SOUL.md</Badge>
          {agentSettings?.workspace && (
            <Badge variant="outline" className="max-w-full truncate">
              {agentSettings.workspace}
            </Badge>
          )}
        </div>
      </div>

      <div className="grid items-stretch gap-6 xl:grid-cols-[minmax(320px,420px)_minmax(0,1fr)]">
        <Card className="flex min-h-[560px] flex-col overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10">
                <Bot className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle>{t("soul.portraitTitle")}</CardTitle>
                <CardDescription>{t("soul.portraitDesc")}</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <div className="flex flex-1 items-center justify-center rounded-2xl border bg-muted/20 p-6">
              <img
                src={portraitSrc}
                alt={t("soul.portraitAlt")}
                className="h-full max-h-[460px] w-auto max-w-full object-contain"
                onError={() => setPortraitSrc("/SOUL.png")}
              />
            </div>
            <div className="mt-4 rounded-xl border bg-background/70 p-4">
              <p className="text-sm font-medium">{t("soul.fileLocation")}</p>
              <p className="mt-1 break-all text-xs text-muted-foreground">
                {agentSettings?.workspace
                  ? `${agentSettings.workspace}\\SOUL.md`
                  : "SOUL.md"}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="flex min-h-[560px] flex-col overflow-hidden">
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle>{t("soul.editorTitle")}</CardTitle>
                  <CardDescription>{t("soul.editorDesc")}</CardDescription>
                </div>
              </div>
              <Badge variant="secondary">
                {t("soul.lineCount", { count: lineCount })}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-4">
            {isLoading ? (
              <Skeleton className="flex-1 rounded-xl" />
            ) : (
              <>
                <Textarea
                  value={content}
                  onChange={(e) => {
                    setContent(e.target.value);
                    setDirty(true);
                  }}
                  className="min-h-0 flex-1 resize-none font-mono text-xs leading-6"
                  style={{ minHeight: "420px" }}
                  spellCheck={false}
                />
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-xs text-muted-foreground">
                    {dirty ? t("settings.unsaved") : t("soul.synced")}
                  </div>
                  <Button
                    type="button"
                    onClick={handleSave}
                    disabled={!dirty || saveWorkspaceFile.isPending}
                  >
                    <Save className="h-4 w-4" />
                    {saveWorkspaceFile.isPending ? t("common.saving") : t("settings.save")}
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
