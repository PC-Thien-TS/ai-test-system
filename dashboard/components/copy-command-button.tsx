"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

type CopyCommandButtonProps = {
  value: string;
};

export function CopyCommandButton({ value }: CopyCommandButtonProps) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      type="button"
      onClick={onCopy}
      className="inline-flex items-center gap-1 rounded border px-2 py-1 text-xs hover:bg-slate-100"
      aria-label="Copy command"
      title="Copy command"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-green-700" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
