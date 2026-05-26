import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useSkills,
  useSkillContent,
  useCreateSkill,
  useUpdateSkill,
  useDeleteSkill,
  useToggleSkill,
} from "../hooks/useSkills";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { ConfirmDialog } from "../components/shared/ConfirmDialog";
import { Skeleton } from "../components/ui/skeleton";
import { Plus, Pencil, Trash2, AlertCircle } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip";

function SkillEditor({
  skillName,
  defaultContent,
  onSave,
  onClose,
}: {
  skillName?: string;
  defaultContent?: string;
  onSave: (name: string, content: string) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(skillName ?? "");
  const [content, setContent] = useState(defaultContent ?? "");
  const { data: existing } = useSkillContent(skillName && !defaultContent ? skillName : "");

  const finalContent = content || existing?.content || "";

  return (
    <>
      <div className="space-y-3 py-2">
        <div className="space-y-1">
          <Label>{t("skills.name")}</Label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={!!skillName}
          />
        </div>
        <div className="space-y-1">
          <Label>{t("skills.content")}</Label>
          <textarea
            className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono h-64 resize-y focus:outline-none focus:ring-2 focus:ring-ring"
            value={content || existing?.content || ""}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
        <Button
          onClick={() => onSave(name, finalContent)}
          disabled={!name || !finalContent}
        >
          {t("skills.save")}
        </Button>
      </DialogFooter>
    </>
  );
}

export default function Skills({ hideTitle }: { hideTitle?: boolean } = {}) {
  const { t } = useTranslation();
  const { data: skills, isLoading } = useSkills();
  const create = useCreateSkill();
  const update = useUpdateSkill();
  const del = useDeleteSkill();
  const toggle = useToggleSkill();

  const [mode, setMode] = useState<"create" | "edit" | null>(null);
  const [targetName, setTargetName] = useState("");
  const [delTarget, setDelTarget] = useState("");

  const handleSave = (name: string, content: string) => {
    if (mode === "create") {
      create.mutate({ name, content });
    } else {
      update.mutate({ name, content });
    }
    setMode(null);
  };

  return (
    <div className="space-y-4">
      <div className={hideTitle ? "flex justify-end" : "flex items-center justify-between"}>
        {!hideTitle && <h1 className="text-2xl font-semibold">{t("skills.title")}</h1>}
        <Button
          size="sm"
          onClick={() => { setTargetName(""); setMode("create"); }}
        >
          <Plus className="mr-2 h-4 w-4" />
          {t("skills.add")}
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("skills.name")}</TableHead>
                <TableHead>{t("skills.description")}</TableHead>
                <TableHead className="w-24">{t("skills.type")}</TableHead>
                <TableHead className="w-28 text-center">{t("skills.available")}</TableHead>
                <TableHead className="w-24 text-center">{t("skills.enabled")}</TableHead>
                <TableHead className="w-20 text-right">{t("common.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {skills?.map((s) => (
                <TableRow key={s.name}>
                  <TableCell className="font-mono font-medium">{s.name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground max-w-xs">
                    <span className="line-clamp-2">{s.description || "—"}</span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={s.source === "builtin" ? "secondary" : "outline"} className="text-xs">
                      {s.source}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    {s.available ? (
                      <Badge variant="default" className="text-xs">{t("skills.available")}</Badge>
                    ) : (
                      <TooltipProvider delayDuration={100}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="inline-flex items-center gap-1 text-xs text-destructive cursor-help">
                              <AlertCircle className="h-3.5 w-3.5" />
                              {t("skills.unavailable")}
                            </span>
                          </TooltipTrigger>
                          {s.unavailable_reason && (
                            <TooltipContent side="top" className="max-w-xs">
                              {s.unavailable_reason}
                            </TooltipContent>
                          )}
                        </Tooltip>
                      </TooltipProvider>
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={s.enabled}
                      disabled={toggle.isPending}
                      onCheckedChange={(enabled) => toggle.mutate({ name: s.name, enabled })}
                    />
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() => { setTargetName(s.name); setMode("edit"); }}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    {s.source === "workspace" && (
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-destructive"
                        onClick={() => setDelTarget(s.name)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {(!skills || skills.length === 0) && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">{t("common.noData")}</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={!!mode} onOpenChange={(v) => !v && setMode(null)}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {mode === "create" ? t("skills.add") : t("skills.edit")}
            </DialogTitle>
          </DialogHeader>
          <SkillEditor
            skillName={mode === "edit" ? targetName : undefined}
            onSave={handleSave}
            onClose={() => setMode(null)}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!delTarget}
        title={t("skills.delete")}
        description={t("skills.deleteConfirm")}
        destructive
        onConfirm={() => { del.mutate(delTarget); setDelTarget(""); }}
        onCancel={() => setDelTarget("")}
      />
    </div>
  );
}
