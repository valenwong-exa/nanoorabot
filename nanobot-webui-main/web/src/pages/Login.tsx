import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api from "../lib/api";
import { useAuthStore } from "../stores/authStore";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "../components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { User, Lock, Languages, BellRing } from "lucide-react";

export default function Login() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      toast.error(t("auth.fieldRequired"));
      return;
    }
    setLoading(true);
    try {
      const res = await api.post("/auth/login", { username, password });
      const { access_token, user } = res.data;
      setAuth(user, access_token);
      navigate("/dashboard");
    } catch {
      toast.error(t("auth.loginFailed"));
    } finally {
      setLoading(false);
    }
  };

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  const LANG_LABELS: Record<string, string> = {
    zh: "中文",
    "zh-TW": "繁體中文",
    en: "English",
    ja: "日本語",
    ko: "한국어",
    de: "Deutsch",
    fr: "Français",
  };

  const getLanguageLabel = () => LANG_LABELS[i18n.language] ?? "English";

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: "url('/backgroud.png')" }}
      />
      <div className="absolute inset-0 bg-white/35 dark:bg-gray-950/55"></div>
      
      {/* 语言切换按钮 */}
      <div className="absolute top-4 right-4 z-10">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2 backdrop-blur-sm bg-white/50 dark:bg-gray-900/50">
              <Languages className="h-4 w-4" />
              {getLanguageLabel()}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => changeLanguage("zh")}>
              中文
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => changeLanguage("zh-TW")}>
              繁體中文
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => changeLanguage("en")}>
              English
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => changeLanguage("ja")}>
              日本語
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => changeLanguage("ko")}>
              한국어
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => changeLanguage("de")}>
              Deutsch
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => changeLanguage("fr")}>
              Français
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="relative z-10 flex w-full max-w-6xl flex-col gap-6 md:flex-row md:items-stretch">
        <Card className="w-full shadow-2xl backdrop-blur-sm bg-white/80 dark:bg-gray-900/80 border-[rgba(162,188,198,0.45)] dark:border-[rgba(162,188,198,0.22)] animate-in fade-in zoom-in duration-500 md:basis-3/5 md:flex md:flex-col">
          <CardHeader className="space-y-3 pb-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[rgba(162,188,198,0.24)] text-[#3B5C69] ring-1 ring-[rgba(162,188,198,0.5)] dark:bg-[rgba(59,92,105,0.3)] dark:text-[#A2BCC6] dark:ring-[rgba(162,188,198,0.22)]">
                  <BellRing className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-2xl font-bold bg-gradient-to-r from-[#3B5C69] to-[#A2BCC6] bg-clip-text text-transparent">
                    Announcement
                  </CardTitle>
                  <CardDescription className="text-sm mt-1">
                    Latest notice
                  </CardDescription>
                </div>
              </div>
              <div className="rounded-full border border-[rgba(162,188,198,0.45)] bg-white/55 px-3 py-1 text-xs font-medium text-[#3B5C69] dark:border-[rgba(162,188,198,0.22)] dark:bg-gray-900/45 dark:text-[#A2BCC6]">
                2026-04-23
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col pt-0">
            <div className="flex-1 rounded-2xl border border-[rgba(162,188,198,0.35)] bg-[rgba(255,255,255,0.42)] p-5 dark:border-[rgba(162,188,198,0.18)] dark:bg-[rgba(15,23,42,0.28)]">
              <div className="mb-4 flex items-center gap-3">
                <div className="h-px flex-1 bg-[rgba(162,188,198,0.55)] dark:bg-[rgba(162,188,198,0.22)]" />
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#3B5C69]/80 dark:text-[#A2BCC6]/80">
                  Bulletin
                </span>
                <div className="h-px flex-1 bg-[rgba(162,188,198,0.55)] dark:bg-[rgba(162,188,198,0.22)]" />
              </div>
              <ol className="list-decimal space-y-2 pl-5 text-sm text-foreground/85">
                <li>welcome to use nanoorabot</li>
              </ol>
            </div>
          </CardContent>
        </Card>

        <Card className="w-full shadow-2xl backdrop-blur-sm bg-white/80 dark:bg-gray-900/80 border-[rgba(162,188,198,0.45)] dark:border-[rgba(162,188,198,0.22)] animate-in fade-in zoom-in duration-500 md:basis-2/5">
          <CardHeader className="text-center space-y-3 pb-4">
            <div className="flex justify-center">
              <div className="relative">
                <div className="absolute inset-0 bg-[rgba(162,188,198,0.35)] dark:bg-[rgba(162,188,198,0.18)] rounded-2xl blur-xl animate-pulse"></div>
                <img 
                  src="/icon.png" 
                  alt="AI System Agent" 
                  className="relative h-16 w-16 rounded-2xl shadow-lg ring-2 ring-[rgba(162,188,198,0.7)] dark:ring-[rgba(162,188,198,0.35)]" 
                />
              </div>
            </div>
            <div>
              <CardTitle className="text-2xl font-bold bg-gradient-to-r from-[#3B5C69] to-[#A2BCC6] bg-clip-text text-transparent">
                NanoOrabot - AI System Agent
              </CardTitle>
              <CardDescription className="text-sm mt-1">{t("auth.login")}</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username" className="text-sm font-medium">
                  {t("auth.username")}
                </Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#3B5C69]" />
                  <Input
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    className="pl-10 h-10 border-[rgba(162,188,198,0.75)] focus-visible:ring-[#3B5C69] bg-gradient-to-r from-[rgba(162,188,198,0.18)] to-white dark:from-[rgba(59,92,105,0.22)] dark:to-gray-800"
                    placeholder={t("auth.username")}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">
                  {t("auth.password")}
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#3B5C69]" />
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    className="pl-10 h-10 border-[rgba(162,188,198,0.75)] focus-visible:ring-[#3B5C69] bg-gradient-to-r from-[rgba(162,188,198,0.18)] to-white dark:from-[rgba(59,92,105,0.22)] dark:to-gray-800"
                    placeholder={t("auth.password")}
                  />
                </div>
              </div>
              <Button 
                type="submit" 
                className="w-full h-10 mt-6 bg-gradient-to-r from-[#3B5C69] to-[#4B7484] hover:from-[#35525D] hover:to-[#3B5C69] text-white font-semibold shadow-xl shadow-[rgba(162,188,198,0.55)] hover:shadow-[rgba(162,188,198,0.75)] transition-all duration-300 hover:scale-[1.02]" 
                disabled={loading}
              >
                {loading ? t("common.loading") : t("auth.loginButton")}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
