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
    <label className="block rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-sm font-semibold text-slate-800">
            {label}
          </p>
          <p className="mt-1 max-w-xl text-xs leading-5 text-slate-500">
            {description}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">
            Permitido: {min}–{max}
            {unit ? ` ${unit}` : ""}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <input
            type="number"
            value={value}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            onChange={event => {
              const next = Number(event.target.value);
              if (Number.isFinite(next)) {
                onChange(next);
              }
            }}
            className="w-28 rounded-lg border border-slate-200 bg-white px-3 py-2 text-right text-sm font-semibold text-slate-800 outline-none transition focus:border-slate-400 disabled:bg-slate-100 disabled:text-slate-400"
          />
          {unit && (
            <span className="w-8 text-xs text-slate-400">
              {unit}
            </span>
          )}
        </div>
      </div>
    </label>
  );
}
