import { CheckCircle2, LoaderCircle, RefreshCw, ServerCrash } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { useRuntimeStatus } from "../contexts/RuntimeStatusContext";
import { animationTokens } from "../lib/animation";
import { formatDateTime } from "../lib/format";

export function RuntimeConnectionBanner() {
  const runtime = useRuntimeStatus();
  const [showRecovery, setShowRecovery] = useState(false);
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    if (!runtime.recoveredAt) return;
    setShowRecovery(true);
    const timer = window.setTimeout(() => setShowRecovery(false), 4500);
    return () => window.clearTimeout(timer);
  }, [runtime.recoveredAt]);

  const animationProps = shouldReduceMotion
    ? {}
    : {
        initial: { opacity: 0, y: -8 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: animationTokens.duration.base, ease: animationTokens.motionEase },
      };

  if (runtime.connection === "connected") {
    return showRecovery ? (
      <motion.div
        {...animationProps}
        className="mb-6 flex items-center gap-3 rounded-2xl border border-[#bceadd] bg-[rgba(239,252,248,0.92)] px-4 py-3 text-sm text-[#18715f] shadow-[0_10px_30px_rgba(40,199,165,0.07)] backdrop-blur-sm"
        role="status"
        aria-live="polite"
      >
        <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-white text-[#28a98f] shadow-sm">
          <CheckCircle2 size={16} />
        </span>
        <div>
          <p className="font-semibold">Conexão com o backend restaurada</p>
          <p className="mt-0.5 text-xs text-[#4d8b7e]">O estado global voltou a ser atualizado pelo serviço local.</p>
        </div>
      </motion.div>
    ) : null;
  }

  if (runtime.connection === "connecting") {
    return (
      <motion.div
        {...animationProps}
        className="mb-6 flex items-center gap-3 rounded-2xl border border-[var(--evil-border)] bg-white/90 px-4 py-3 text-sm text-[var(--evil-text-muted)] shadow-[var(--evil-shadow-sm)] backdrop-blur-sm"
        role="status"
        aria-live="polite"
      >
        <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-[#edf1ff] text-[#4968e8]">
          <LoaderCircle size={16} className="animate-spin" />
        </span>
        Verificando o backend local…
      </motion.div>
    );
  }

  return (
    <motion.div
      {...animationProps}
      className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-amber-200/80 bg-[rgba(255,249,235,0.94)] px-4 py-3.5 shadow-[0_10px_30px_rgba(180,120,20,0.06)] backdrop-blur-sm max-[560px]:items-stretch"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl border border-amber-200 bg-white text-amber-700 shadow-sm">
          <ServerCrash size={17} />
        </span>
        <div>
          <p className="text-sm font-semibold text-amber-950">
            {runtime.connection === "disconnected" ? "Backend local desconectado" : "Reconectando ao backend local"}
          </p>
          <p className="mt-1 max-w-4xl text-xs leading-5 text-amber-800/75">
            O aplicativo mantém os dados já carregados, mas o estado de scanner, modelo e scheduler não deve ser interpretado como atual até a conexão voltar.
            {runtime.lastConnectedAt ? ` Última conexão: ${formatDateTime(runtime.lastConnectedAt)}.` : ""}
          </p>
        </div>
      </div>
      <button type="button" className="btn-secondary max-[560px]:w-full" disabled={runtime.checking} onClick={() => void runtime.refresh()}>
        <RefreshCw size={15} className={runtime.checking ? "animate-spin" : ""} />
        Tentar agora
      </button>
    </motion.div>
  );
}
