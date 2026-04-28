import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.floor((today.getTime() - dateOnly.getTime()) / 86400000);
  const timeStr = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (diffDays === 0) return timeStr;
  if (diffDays === 1) return `${date.getMonth() + 1}/${date.getDate()} ${timeStr}`;
  if (diffDays < 180) return `${date.getMonth() + 1}/${date.getDate()}`;
  return date.toLocaleDateString([], { year: "numeric", month: "short" });
}

export function maskSecret(value: string): string {
  if (!value) return "";
  if (value.startsWith("••••")) return value;
  const last4 = value.slice(-4);
  return `••••${last4}`;
}

export function isMasked(value: string): boolean {
  return value.startsWith("••••");
}
