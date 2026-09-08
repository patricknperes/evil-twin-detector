import { motion, useReducedMotion } from "motion/react";
import { animationTokens } from "../../lib/animation";
import { AmbientNetworkScene } from "./AmbientNetworkScene";
import { SignalPulseField } from "./SignalPulseField";

export function NetworkBackdrop() {
  const shouldReduceMotion = useReducedMotion();
  const reducedMotion = Boolean(shouldReduceMotion);

  return (
    <motion.div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
      initial={reducedMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: animationTokens.duration.slow, ease: animationTokens.motionEase }}
      aria-hidden="true"
    >
      <div className="evil-ambient-grid absolute inset-0" />
      <div className="evil-ambient-glow evil-ambient-glow--indigo" />
      <div className="evil-ambient-glow evil-ambient-glow--mint" />
      <div className="absolute inset-y-0 right-0 w-[54%] opacity-75">
        <AmbientNetworkScene reducedMotion={reducedMotion} />
      </div>
      <SignalPulseField reducedMotion={reducedMotion} />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(247,248,252,0.98)_0%,rgba(247,248,252,0.95)_30%,rgba(247,248,252,0.68)_67%,rgba(247,248,252,0.58)_100%)]" />
    </motion.div>
  );
}
