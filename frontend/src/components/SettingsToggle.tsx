import { Check, X } from "lucide-react";
import { motion } from "motion/react";

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
        "group relative flex min-h-32 items-start justify-between gap-5 overflow-hidden rounded-[1.15rem] border p-4 transition max-[560px]:flex-col max-[560px]:gap-4",
        checked
          ? "border-indigo-100 bg-indigo-50/55 shadow-[0_10px_28px_rgba(73,104,232,0.06)]"
          : "border-slate-200/90 bg-white hover:border-slate-300 hover:shadow-[0_10px_28px_rgba(34,39,76,0.045)]",
        disabled
          ? "cursor-not-allowed opacity-55"
          : "cursor-pointer"
      ].join(" ")}
    >
      <span
        aria-hidden="true"
        className={[
          "absolute inset-y-0 left-0 w-1 transition-colors",
          checked ? "bg-[#4968e8]" : "bg-transparent"
        ].join(" ")}
      />

      <span className="min-w-0 pr-1">
        <span className="flex items-center gap-2">
          <span className="text-sm font-semibold tracking-[-0.01em] text-slate-800">
            {label}
          </span>
          <span
            className={[
              "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.09em]",
              checked
                ? "bg-indigo-100 text-indigo-700"
                : "bg-slate-100 text-slate-500"
            ].join(" ")}
          >
            {checked ? "Ativo" : "Inativo"}
          </span>
        </span>
        <span className="mt-2 block max-w-2xl text-xs leading-5 text-slate-500">
          {description}
        </span>
      </span>

      <span className="relative mt-0.5 inline-flex shrink-0 max-[560px]:self-end">
        <input
          type="checkbox"
          className="peer sr-only"
          checked={checked}
          disabled={disabled}
          onChange={(event: { target: { checked: boolean } }) => onChange(event.target.checked)}
        />
        <span
          className={[
            "relative h-7 w-[3.25rem] rounded-full border transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-300 peer-focus-visible:ring-offset-2",
            checked
              ? "border-[#4968e8] bg-[#4968e8]"
              : "border-slate-200 bg-slate-200"
          ].join(" ")}
        >
          <motion.span
            aria-hidden="true"
            animate={{ x: checked ? 24 : 2 }}
            transition={{ type: "spring", stiffness: 500, damping: 34 }}
            className="absolute top-[2px] grid size-[22px] place-items-center rounded-full bg-white shadow-[0_2px_7px_rgba(31,41,75,0.18)]"
          >
            {checked ? (
              <Check size={12} className="text-[#4968e8]" strokeWidth={3} />
            ) : (
              <X size={11} className="text-slate-400" strokeWidth={2.5} />
            )}
          </motion.span>
        </span>
      </span>
    </label>
  );
}
