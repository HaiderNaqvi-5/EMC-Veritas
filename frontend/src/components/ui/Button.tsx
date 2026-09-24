import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "../../lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({ className, variant = "primary", ...props }, ref) {
  return <button ref={ref} className={cn("inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 disabled:pointer-events-none disabled:opacity-60", variant === "primary" && "bg-[#bd263e] text-white shadow-[0_10px_30px_rgba(189,38,62,.26)] hover:bg-[#d6324d]", variant === "secondary" && "border border-white/25 bg-white/5 text-white hover:bg-white/10", variant === "ghost" && "text-slate-700 hover:bg-slate-100", className)} {...props} />;
});
