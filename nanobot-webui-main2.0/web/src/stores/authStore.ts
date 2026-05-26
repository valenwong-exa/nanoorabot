import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface UserInfo {
  id: string;
  username: string;
  role: "admin" | "user";
}

interface AuthState {
  user: UserInfo | null;
  token: string | null;
  setAuth: (user: UserInfo, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => set({ user, token }),
      clearAuth: () => set({ user: null, token: null }),
    }),
    {
      name: "nanobot-auth",
    }
  )
);
