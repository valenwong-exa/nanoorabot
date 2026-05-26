import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api from "../../lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

interface ChangePasswordDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ChangePasswordDialog({
  open,
  onClose,
}: ChangePasswordDialogProps) {
  const { t } = useTranslation();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (next !== confirm) {
      toast.error(t("auth.passwordMismatch"));
      return;
    }
    setLoading(true);
    try {
      await api.put("/auth/password", {
        current_password: current,
        new_password: next,
      });
      toast.success(t("auth.passwordChanged"));
      setCurrent("");
      setNext("");
      setConfirm("");
      onClose();
    } catch {
      toast.error(t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("auth.changePassword")}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <Label>{t("auth.currentPassword")}</Label>
            <Input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>{t("auth.newPassword")}</Label>
            <Input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>{t("auth.confirmPassword")}</Label>
            <Input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            {t("common.cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
