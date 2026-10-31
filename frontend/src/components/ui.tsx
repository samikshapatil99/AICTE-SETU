import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...a: any[]) { return twMerge(clsx(a)); }

export function Card({ className, children }: any) {
  return <div className={cn("bg-white rounded-xl shadow-sm border border-slate-200", className)}>{children}</div>;
}
export function CardHeader({ className, children }: any) {
  return <div className={cn("px-6 py-4 border-b border-slate-100", className)}>{children}</div>;
}
export function CardTitle({ className, children }: any) {
  return <h3 className={cn("font-semibold text-slate-800", className)}>{children}</h3>;
}
export function CardContent({ className, children }: any) {
  return <div className={cn("px-6 py-4", className)}>{children}</div>;
}

export function Button({ className, variant = "default", size = "md", ...props }: any) {
  const base = "inline-flex items-center justify-center rounded-md font-medium transition disabled:opacity-50 disabled:pointer-events-none";
  const variants: any = {
    default: "bg-navy-600 text-white hover:bg-navy-700",
    secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200",
    destructive: "bg-red-600 text-white hover:bg-red-700",
    outline: "border border-slate-300 bg-white hover:bg-slate-50",
    ghost: "hover:bg-slate-100",
  };
  const sizes: any = { sm: "h-8 px-3 text-xs", md: "h-10 px-4 text-sm", lg: "h-12 px-6 text-base" };
  return <button className={cn(base, variants[variant], sizes[size], className)} {...props} />;
}

export function Badge({ className, variant = "default", children }: any) {
  const variants: any = {
    default: "bg-slate-100 text-slate-800",
    success: "bg-green-100 text-green-700",
    warning: "bg-amber-100 text-amber-700",
    destructive: "bg-red-100 text-red-700",
    info: "bg-blue-100 text-blue-700",
  };
  return <span className={cn("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium", variants[variant], className)}>{children}</span>;
}

export function Input({ className, ...props }: any) {
  return <input className={cn("w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-500", className)} {...props} />;
}
export function Select({ className, children, ...props }: any) {
  return <select className={cn("w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-500", className)} {...props}>{children}</select>;
}
export function Label({ className, children }: any) {
  return <label className={cn("block text-sm font-medium text-slate-700 mb-1", className)}>{children}</label>;
}