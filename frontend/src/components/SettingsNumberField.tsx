interface Props {
  label: string;
  description: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (value: number) => void;
  disabled?: boolean;
}

export function SettingsNumberField({
  label,
  description,
  value,
  min,
  max,
  step = 1,
  unit,
  onChange,
  disabled = false
}: Props) {
  return (
    <label
      className={[
        "group block min-h-32 rounded-[1.15rem] border border-slate-200/90 bg-white p-4 transition",
        disabled
          ? "cursor-not-allowed opacity-55"
          : "hover:border-slate-300 hover:shadow-[0_10px_28px_rgba(34,39,76,0.045)]"
      ].join(" ")}
    >
      <span className="flex items-start justify-between gap-5 max-[560px]:flex-col max-[560px]:gap-4">
        <span className="min-w-0">
          <span className="block text-sm font-semibold tracking-[-0.01em] text-slate-800">
            {label}
          </span>
          <span className="mt-2 block max-w-xl text-xs leading-5 text-slate-500">
            {description}
          </span>
        </span>

        <span className="flex shrink-0 items-stretch overflow-hidden rounded-xl border border-slate-200 bg-slate-50 shadow-inner transition group-focus-within:border-indigo-300 group-focus-within:ring-2 group-focus-within:ring-indigo-100 max-[560px]:self-end">
          <input
            type="number"
            value={value}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            onChange={(event: { target: { value: string } }) => {
              const next = Number(event.target.value);
              if (Number.isFinite(next)) {
                onChange(next);
              }
            }}
            className="w-24 bg-transparent px-3 py-2.5 text-right text-sm font-bold tabular-nums text-slate-800 outline-none disabled:text-slate-400"
          />
          {unit && (
            <span className="grid min-w-10 place-items-center border-l border-slate-200 bg-white px-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              {unit}
            </span>
          )}
        </span>
      </span>

      <span className="mt-4 flex items-center gap-3">
        <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
          <span
            className="block h-full rounded-full bg-gradient-to-r from-[#4968e8] to-[#2ac7a9] transition-[width] duration-300"
            style={{
              width: `${Math.max(0, Math.min(100, ((value - min) / Math.max(1, max - min)) * 100))}%`
            }}
          />
        </span>
        <span className="shrink-0 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">
          {min}–{max}{unit ? ` ${unit}` : ""}
        </span>
      </span>
    </label>
  );
}
