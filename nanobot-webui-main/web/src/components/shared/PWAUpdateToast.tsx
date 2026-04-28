import { useEffect } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";

/**
 * Listens for PWA service-worker updates and shows a sonner toast with a
 * one-click "Reload" button when a new version is ready to install.
 *
 * Must be rendered inside <Toaster> and <I18nextProvider>.
 */
export function PWAUpdateToast() {
  const { t } = useTranslation();
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    // Called when a new SW has finished installing and is waiting to take over.
    onNeedRefresh() {
      // handled via needRefresh state below
    },
  });

  useEffect(() => {
    if (!needRefresh) return;

    toast(t("pwa.updateAvailable"), {
      duration: Infinity,        // keep until dismissed or acted on
      id: "pwa-update",          // prevent duplicate toasts
      action: {
        label: t("pwa.reload"),
        onClick: () => updateServiceWorker(true),
      },
      cancel: {
        label: t("common.dismiss"),
        onClick: () => toast.dismiss("pwa-update"),
      },
    });
  }, [needRefresh, updateServiceWorker, t]);

  return null;
}
