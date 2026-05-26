import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api from "../lib/api";
import { useAuthStore } from "../stores/authStore";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
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
import { ConfirmDialog } from "../components/shared/ConfirmDialog";
import { Plus, Trash2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

interface UserInfo {
  id: string;
  username: string;
  role: "admin" | "user";
}

export default function Users() {
  const { t } = useTranslation();
  const currentUser = useAuthStore((s) => s.user);
  const qc = useQueryClient();

  const { data: users, isLoading } = useQuery<UserInfo[]>({
    queryKey: ["users"],
    queryFn: () => api.get("/users").then((r) => r.data),
  });

  const createUser = useMutation({
    mutationFn: (data: { username: string; password: string; role: string }) =>
      api.post("/users", data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success(t("users.created"));
      setOpen(false);
    },
  });

  const deleteUser = useMutation({
    mutationFn: (id: string) => api.delete(`/users/${id}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success(t("users.deleted"));
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg ?? t("common.error"));
    },
  });

  const [open, setOpen] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "user">("user");
  const [delTarget, setDelTarget] = useState<string | null>(null);

  const handleCreate = () => {
    createUser.mutate({ username: newUsername, password: newPassword, role: newRole });
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setNewUsername(""); setNewPassword(""); setNewRole("user"); setOpen(true); }}>
          <Plus className="mr-2 h-4 w-4" />
          {t("users.add")}
        </Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("users.username")}</TableHead>
              <TableHead>{t("users.role")}</TableHead>
              <TableHead className="w-20 text-right">{t("common.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users?.map((u) => (
              <TableRow key={u.id}>
                <TableCell className="font-mono font-medium">
                  {u.username}
                  {u.id === currentUser?.id && (
                    <span className="ml-2 text-xs text-muted-foreground">(you)</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant={u.role === "admin" ? "default" : "secondary"}>
                    {u.role === "admin" ? t("users.admin") : t("users.user")}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {u.id !== currentUser?.id && (
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 text-destructive"
                      onClick={() => setDelTarget(u.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {(!users || users.length === 0) && !isLoading && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">{t("common.noData")}</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{t("users.add")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1">
              <Label>{t("users.username")}</Label>
              <Input value={newUsername} onChange={(e) => setNewUsername(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>{t("auth.password")}</Label>
              <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>{t("users.role")}</Label>
              <Select value={newRole} onValueChange={(v) => setNewRole(v as "admin" | "user")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">{t("users.user")}</SelectItem>
                  <SelectItem value="admin">{t("users.admin")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>{t("common.cancel")}</Button>
            <Button onClick={handleCreate} disabled={!newUsername || !newPassword || createUser.isPending}>
              {t("common.add")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!delTarget}
        title={t("users.delete")}
        description={t("users.deleteConfirm")}
        destructive
        onConfirm={() => { if (delTarget) deleteUser.mutate(delTarget); setDelTarget(null); }}
        onCancel={() => setDelTarget(null)}
      />
    </div>
  );
}
