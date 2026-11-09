/* Accessible building blocks on top of Radix primitives. Every interactive control has a name and a visible focus state. */
import * as AlertDialog from "@radix-ui/react-alert-dialog";
import * as Dialog from "@radix-ui/react-dialog";
import * as RadixSelect from "@radix-ui/react-select";
import * as Switch from "@radix-ui/react-switch";
import * as RadixToast from "@radix-ui/react-toast";
import * as RadixTooltip from "@radix-ui/react-tooltip";
import { AlertTriangle, Check, CheckCircle2, ChevronDown, CircleHelp, Copy, Info, RefreshCw, XCircle } from "lucide-react";
import { createContext, forwardRef, useCallback, useContext, useId, useMemo, useState, type ComponentProps, type ReactNode } from "react";

import { ApiError } from "@/api/client";

type ButtonProps = ComponentProps<"button"> & { variant?: "primary" | "ghost" | "hint" | "danger"; size?: "small"; block?: boolean; icon?: boolean };
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({ variant, size, block, icon, className = "", ...rest }, ref) {
  const classes = ["btn", variant && `btn-${variant}`, size && `btn-${size}`, block && "btn-block", icon && "btn-icon", className].filter(Boolean).join(" ");
  return <button ref={ref} type="button" className={classes} {...rest} />;
});

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return (
    <Tip text={copied ? "Copied" : label}>
      <Button variant="ghost" size="small" icon aria-label={copied ? "Copied" : label} onClick={() => void copy()}>
        {copied ? <Check size={13} aria-hidden /> : <Copy size={13} aria-hidden />}
      </Button>
    </Tip>
  );
}

export function Spinner({ label }: { label?: string }) {
  return <span className="spinner" role={label ? "status" : undefined} aria-label={label} />;
}

export function Tip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <RadixTooltip.Root delayDuration={250}>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content className="tooltip" sideOffset={5}>{text}</RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}

/** A short explanation available on demand. Uses a dialog rather than a tooltip, so it works with touch and screen readers. */
export function HelpDialog({ title, label, children }: { title: string; label?: string; children: ReactNode }) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        {label ? <button type="button" className="btn-link">{label}</button> : <button type="button" className="btn btn-ghost btn-small btn-icon" aria-label={`Explain: ${title}`}><CircleHelp size={15} /></button>}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content" aria-describedby={undefined}>
          <Dialog.Title asChild><h2>{title}</h2></Dialog.Title>
          <div className="stack-s">{children}</div>
          <div className="dialog-actions"><Dialog.Close asChild><Button>Close</Button></Dialog.Close></div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function Modal({ open, onOpenChange, title, children }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; children: ReactNode }) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content" aria-describedby={undefined}>
          <Dialog.Title asChild><h2>{title}</h2></Dialog.Title>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function Confirm({ trigger, title, description, confirmLabel, onConfirm, destructive }: { trigger: ReactNode; title: string; description: string; confirmLabel: string; onConfirm: () => void; destructive?: boolean }) {
  return (
    <AlertDialog.Root>
      <AlertDialog.Trigger asChild>{trigger}</AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="dialog-overlay" />
        <AlertDialog.Content className="dialog-content">
          <AlertDialog.Title asChild><h2>{title}</h2></AlertDialog.Title>
          <AlertDialog.Description asChild><p className="muted">{description}</p></AlertDialog.Description>
          <div className="dialog-actions">
            <AlertDialog.Cancel asChild><Button>Cancel</Button></AlertDialog.Cancel>
            <AlertDialog.Action asChild><Button variant={destructive ? "danger" : "primary"} onClick={onConfirm}>{confirmLabel}</Button></AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}

export function Field({ label, help, error, children }: { label: string; help?: ReactNode; error?: string | null; children: (props: { id: string; "aria-describedby"?: string; "aria-invalid"?: boolean }) => ReactNode }) {
  const id = useId();
  const describedBy = [help ? `${id}-help` : null, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className="field">
      <label className="field-label" htmlFor={id}>{label}</label>
      {help && <div className="field-help" id={`${id}-help`}>{help}</div>}
      {children({ id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })}
      {error && <div className="field-error" id={`${id}-error`}>{error}</div>}
    </div>
  );
}

export function Select({ value, onChange, options, label, placeholder }: { value: string; onChange: (value: string) => void; options: { value: string; label: string }[]; label: string; placeholder?: string }) {
  return (
    <RadixSelect.Root value={value} onValueChange={onChange}>
      <RadixSelect.Trigger className="select-trigger" aria-label={label}>
        <RadixSelect.Value placeholder={placeholder ?? label} />
        <RadixSelect.Icon><ChevronDown size={15} /></RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content className="select-content" position="popper" sideOffset={4}>
          <RadixSelect.Viewport className="select-viewport">
            {options.map((option) => (
              <RadixSelect.Item key={option.value} value={option.value} className="select-item">
                <RadixSelect.ItemIndicator className="select-indicator"><Check size={14} /></RadixSelect.ItemIndicator>
                <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return (
    <Switch.Root className="switch" checked={checked} onCheckedChange={onChange} aria-label={label}>
      <Switch.Thumb className="switch-thumb" />
    </Switch.Root>
  );
}

export function Notice({ tone = "info", children, title }: { tone?: "info" | "warn" | "danger" | "ok"; children?: ReactNode; title?: string }) {
  const Icon = tone === "danger" ? XCircle : tone === "warn" ? AlertTriangle : tone === "ok" ? CheckCircle2 : Info;
  return (
    <div className={`notice notice-${tone}`} role={tone === "danger" ? "alert" : undefined}>
      <Icon size={17} aria-hidden />
      <div className="grow stack-s" style={{ gap: 2 }}>
        {title && <strong>{title}</strong>}
        {children && <div>{children}</div>}
      </div>
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children && <p className="prose">{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry, what = "This page" }: { error: unknown; onRetry?: () => void; what?: string }) {
  const message = error instanceof ApiError ? error.message : `${what} could not be loaded.`;
  return (
    <div className="empty" role="alert">
      <h3>{what} could not be loaded</h3>
      <p className="prose">{message}</p>
      {onRetry && <Button onClick={onRetry}><RefreshCw size={15} aria-hidden /> Try again</Button>}
    </div>
  );
}

export function PageLoading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="stack" role="status" aria-label={label}>
      <div className="skeleton" style={{ height: 34, width: "40%" }} />
      <div className="skeleton" style={{ height: 110 }} />
      <div className="skeleton" style={{ height: 180 }} />
    </div>
  );
}

export function Stat({ value, label, note }: { value: ReactNode; label: string; note?: ReactNode }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {note && <span className="stat-note">{note}</span>}
    </div>
  );
}

/* ---- Notifications ---- */
type ToastItem = { id: number; tone: "ok" | "error" | "info"; title: string; detail?: string };
const ToastContext = createContext<(toast: Omit<ToastItem, "id">) => void>(() => undefined);
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const add = useCallback((toast: Omit<ToastItem, "id">) => setItems((list) => [...list.slice(-2), { ...toast, id: Date.now() + Math.random() }]), []);
  const value = useMemo(() => add, [add]);
  return (
    <ToastContext.Provider value={value}>
      <RadixToast.Provider duration={5000} swipeDirection="right">
        {children}
        {items.map((item) => {
          const Icon = item.tone === "ok" ? CheckCircle2 : item.tone === "error" ? XCircle : Info;
          return (
            <RadixToast.Root key={item.id} className={`toast toast-${item.tone}`} onOpenChange={(open) => !open && setItems((list) => list.filter((t) => t.id !== item.id))}>
              <Icon size={17} aria-hidden />
              <div className="grow">
                <RadixToast.Title className="toast-title">{item.title}</RadixToast.Title>
                {item.detail && <RadixToast.Description className="muted">{item.detail}</RadixToast.Description>}
              </div>
              <RadixToast.Close className="btn btn-ghost btn-small" aria-label="Dismiss">✕</RadixToast.Close>
            </RadixToast.Root>
          );
        })}
        <RadixToast.Viewport className="toast-viewport" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}

export function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Your work is safe. Please try again.";
}
