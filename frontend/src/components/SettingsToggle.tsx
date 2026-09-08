interface Props {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description: string;
  disabled?: boolean;
}

export function SettingsToggle({
  checked,
  onChange,
  label,
  description,
  disabled = false
}: Props) {
  return (
    <label
      className={[
        "flex items-center justify-between gap-6 rounded-xl border border-slate-200 bg-white p-4",
        disabled
          ? "cursor-not-allowed opacity-60"
          : "cursor-pointer"
      ].join(" ")}
    >
      <div>
        <p className="text-sm font-semibold text-slate-800">
          {label}
        </p>
        <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-500">
          {description}
        </p>
      </div>

      <span className="relative inline-flex shrink-0">
        <input
          type="checkbox"
          className="peer sr-only"
          checked={checked}
          disabled={disabled}
          onChange={event =>
            onChange(event.target.checked)
          }
        />
        <span className="h-6 w-11 rounded-full bg-slate-200 transition peer-checked:bg-slate-900 peer-focus-visible:ring-2 peer-focus-visible:ring-slate-400 peer-focus-visible:ring-offset-2" />
        <span className="pointer-events-none absolute left-0.5 top-0.5 size-5 rounded-full bg-white shadow-sm transition peer-checked:translate-x-5" />
      </span>
    </label>
  );
}
