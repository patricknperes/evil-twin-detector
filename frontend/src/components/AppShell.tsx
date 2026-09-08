import {
  Activity,
  BarChart3,
  History,
  Radar,
  Settings,
  ShieldCheck,
  Wifi,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { NavLink, Outlet } from "react-router-dom";
import { animationTokens } from "../lib/animation";
import { RuntimeConnectionBanner } from "./RuntimeConnectionBanner";
import { RuntimeStatusPanel } from "./RuntimeStatusPanel";
import { NetworkBackdrop } from "./visual/NetworkBackdrop";

type NavigationItem = {
  to: string;
  label: string;
  icon: LucideIcon;
};

const monitoringNavigation: NavigationItem[] = [
  { to: "/", label: "Visão geral", icon: BarChart3 },
  { to: "/scan", label: "Escanear redes", icon: Radar },
  { to: "/networks", label: "Redes observadas", icon: Wifi },
  { to: "/history", label: "Histórico", icon: History },
  { to: "/model", label: "Modelo", icon: Activity },
];

const systemNavigation: NavigationItem[] = [
  { to: "/diagnostics", label: "Diagnóstico", icon: Wrench },
  { to: "/settings", label: "Configurações", icon: Settings },
];

export function AppShell() {
  const shouldReduceMotion = useReducedMotion();
  const reducedMotion = Boolean(shouldReduceMotion);

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[var(--evil-bg)]">
      <a href="#main-content" className="evil-skip-link">Pular para o conteúdo</a>
      <NetworkBackdrop />

      <aside className="fixed inset-y-4 left-4 z-30 w-[276px] overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,#353c7d_0%,#2b326d_48%,#232957_100%)] shadow-[0_24px_70px_rgba(35,41,87,0.24)] max-[1180px]:w-[88px] max-[760px]:inset-x-3 max-[760px]:bottom-3 max-[760px]:top-auto max-[760px]:h-[76px] max-[760px]:w-auto max-[760px]:rounded-[22px]">
        <div className="relative flex h-full flex-col">
          <div className="pointer-events-none absolute -right-20 -top-24 size-56 rounded-full border border-white/10" />
          <div className="pointer-events-none absolute -right-8 -top-10 size-32 rounded-full bg-[#28c7a5]/10 blur-2xl" />

          <div className="relative flex min-h-[104px] items-center gap-3.5 border-b border-white/10 px-5 max-[1180px]:justify-center max-[1180px]:px-3 max-[760px]:hidden">
            <div className="relative grid size-12 shrink-0 place-items-center rounded-2xl border border-white/15 bg-white text-[#343b78] shadow-[0_12px_28px_rgba(15,20,60,0.2)]">
              <ShieldCheck size={24} strokeWidth={2.1} />
              <span className="absolute -right-0.5 -top-0.5 size-3.5 rounded-full border-[3px] border-[#353c7d] bg-[#28c7a5]" aria-hidden="true" />
            </div>

            <div className="min-w-0 max-[1180px]:hidden">
              <p className="truncate text-[15px] font-semibold tracking-[-0.02em] text-white">Evil Twin Detector</p>
              <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/45">Wi-Fi security monitor</p>
            </div>
          </div>

          <div className="evil-nav-scroll relative flex min-h-0 flex-1 flex-col overflow-y-auto px-3.5 py-5 max-[1180px]:px-2.5 max-[760px]:flex-row max-[760px]:items-center max-[760px]:overflow-x-auto max-[760px]:overflow-y-hidden max-[760px]:p-2">
            <NavigationGroup label="Monitoramento" items={monitoringNavigation} reducedMotion={reducedMotion} />
            <div className="my-4 border-t border-white/10 max-[760px]:mx-1 max-[760px]:my-0 max-[760px]:h-8 max-[760px]:border-l max-[760px]:border-t-0" />
            <NavigationGroup label="Sistema" items={systemNavigation} reducedMotion={reducedMotion} />
          </div>

          <div className="relative space-y-3 border-t border-white/10 p-3.5 max-[1180px]:p-2.5 max-[760px]:hidden">
            <RuntimeStatusPanel />

            <div className="evil-sidebar-guidance rounded-2xl border border-white/10 bg-white/[0.055] px-3.5 py-3.5 text-[11px] leading-[1.65] text-white/55 max-[1180px]:hidden">
              <div className="mb-2 flex items-center gap-2">
                <span className="size-1.5 rounded-full bg-[#28c7a5] shadow-[0_0_0_4px_rgba(40,199,165,0.1)]" />
                <p className="font-semibold text-white/85">Interpretação responsável</p>
              </div>
              <p>O sistema indica anomalias e níveis de suspeita. Não confirma um ataque Evil Twin.</p>
            </div>
          </div>
        </div>
      </aside>

      <main id="main-content" tabIndex={-1} className="relative z-10 min-h-screen pl-[308px] transition-[padding] duration-300 max-[1180px]:pl-[120px] max-[760px]:pb-[104px] max-[760px]:pl-0">
        <div className="mx-auto w-full max-w-[1540px] px-8 py-7 max-[900px]:px-5 max-[560px]:px-4 max-[560px]:py-5">
          <RuntimeConnectionBanner />
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function NavigationGroup({
  label,
  items,
  reducedMotion,
}: {
  label: string;
  items: NavigationItem[];
  reducedMotion: boolean;
}) {
  return (
    <div className="max-[760px]:shrink-0">
      <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/35 max-[1180px]:sr-only">{label}</p>
      <nav className="space-y-1 max-[760px]:flex max-[760px]:gap-1 max-[760px]:space-y-0" aria-label={label}>
        {items.map((item) => (
          <NavigationLink key={item.to} item={item} reducedMotion={reducedMotion} />
        ))}
      </nav>
    </div>
  );
}

function NavigationLink({ item, reducedMotion }: { item: NavigationItem; reducedMotion: boolean }) {
  const Icon = item.icon;

  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      aria-label={item.label}
      title={item.label}
      className="group relative flex min-h-12 items-center gap-3 overflow-hidden rounded-2xl px-3 text-[13px] font-medium outline-none max-[1180px]:justify-center max-[1180px]:px-2 max-[760px]:size-12 max-[760px]:min-h-0 max-[760px]:shrink-0"
    >
      {({ isActive }) => (
        <>
          {isActive ? (
            <motion.span
              layoutId="sidebar-active-navigation"
              className="absolute inset-0 rounded-2xl bg-white shadow-[0_10px_24px_rgba(17,22,62,0.18)]"
              transition={
                reducedMotion
                  ? { duration: 0 }
                  : { duration: animationTokens.duration.base, ease: animationTokens.motionEase }
              }
              aria-hidden="true"
            />
          ) : (
            <span className="absolute inset-0 rounded-2xl bg-white/0 transition-colors duration-200 group-hover:bg-white/[0.075]" aria-hidden="true" />
          )}

          <span
            className={[
              "relative z-10 grid size-8 shrink-0 place-items-center rounded-xl transition-colors duration-200",
              isActive ? "bg-[#edf1ff] text-[#4968e8]" : "bg-white/[0.075] text-white/65 group-hover:bg-white/10 group-hover:text-white",
            ].join(" ")}
          >
            <Icon size={17} strokeWidth={2} />
          </span>

          <span
            className={[
              "relative z-10 min-w-0 flex-1 truncate transition-colors duration-200 max-[1180px]:hidden",
              isActive ? "font-semibold text-[#292f62]" : "text-white/68 group-hover:text-white",
            ].join(" ")}
          >
            {item.label}
          </span>

          <span
            className={[
              "relative z-10 size-1.5 shrink-0 rounded-full transition-all duration-200 max-[1180px]:hidden",
              isActive ? "bg-[#28c7a5] opacity-100" : "bg-white opacity-0 group-hover:opacity-25",
            ].join(" ")}
            aria-hidden="true"
          />
        </>
      )}
    </NavLink>
  );
}
