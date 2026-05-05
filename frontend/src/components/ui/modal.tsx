import { X } from "lucide-react";
import type { ReactNode } from "react";

interface ModalProps {
  children: ReactNode;
  isOpen: boolean;
  onClose: () => void;
  title: string;
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fade-in fixed inset-0 z-50 flex animate-in items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm duration-200">
      <div className="zoom-in-95 flex max-h-[90vh] w-full max-w-5xl animate-in flex-col overflow-hidden rounded-2xl bg-white shadow-2xl duration-200 dark:bg-slate-950">
        <div className="flex items-center justify-between border-slate-100 border-b p-6 dark:border-slate-800">
          <h2 className="font-bold text-xl tracking-tight">{title}</h2>
          <button
            className="rounded-full p-2 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
            onClick={onClose}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </div>
    </div>
  );
}
