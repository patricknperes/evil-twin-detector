import { useEffect, useRef } from "react";
import { animate } from "animejs";

interface SignalPulseFieldProps {
  reducedMotion?: boolean;
}

const pulsePositions = [
  { cx: 78, cy: 54, r: 16 },
  { cx: 170, cy: 126, r: 20 },
  { cx: 118, cy: 208, r: 13 },
];

export function SignalPulseField({ reducedMotion = false }: SignalPulseFieldProps) {
  const rootRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || reducedMotion) return undefined;

    const pulseNodes = Array.from(root.querySelectorAll<SVGCircleElement>("[data-network-pulse]"));
    const animations = pulseNodes.map((node, index) =>
      animate(node, {
        opacity: [0.12, 0.42, 0.12],
        scale: [0.94, 1.08, 0.94],
        duration: 3800 + index * 620,
        delay: index * 420,
        ease: "inOutSine",
        loop: true,
      }),
    );

    return () => animations.forEach((animation) => animation.cancel());
  }, [reducedMotion]);

  return (
    <svg
      ref={rootRef}
      viewBox="0 0 240 280"
      className="absolute right-[5%] top-[8%] h-[420px] w-[360px] max-w-[34vw] opacity-70"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="network-pulse-gradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#6475d6" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#2ac7a9" stopOpacity="0.18" />
        </linearGradient>
      </defs>

      {pulsePositions.map(({ cx, cy, r }, index) => (
        <g key={`${cx}-${cy}`}>
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke="url(#network-pulse-gradient)"
            strokeWidth="1"
            opacity={reducedMotion ? 0.2 : 0.12}
            data-network-pulse
            className="network-pulse-ring"
          />
          <circle cx={cx} cy={cy} r="2.2" fill={index === 1 ? "#2ac7a9" : "#586acb"} opacity="0.52" />
        </g>
      ))}

      <path d="M78 54 L170 126 L118 208" fill="none" stroke="#7180d2" strokeWidth="0.65" opacity="0.16" />
      <path d="M78 54 L118 208" fill="none" stroke="#7180d2" strokeWidth="0.65" opacity="0.1" />
    </svg>
  );
}
