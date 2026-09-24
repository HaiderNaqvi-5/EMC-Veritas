import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Shared shadcn-compatible class-name helper. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
