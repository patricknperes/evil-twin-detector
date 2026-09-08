import { useEffect, useMemo, useRef } from "react";
import { animate } from "animejs";
import { gsap } from "gsap";
import * as THREE from "three";

import { prefersReducedMotion } from "../../lib/animation";

interface ScanRadarSceneProps {
  active: boolean;
  networkCount?: number;
  highRiskCount?: number;
}

function seededPoint(index: number, total: number): [number, number, number] {
  const angle = (index / Math.max(total, 1)) * Math.PI * 2 + (index % 3) * 0.29;
  const radius = 0.9 + ((index * 37) % 100) / 100 * 2.3;
  const y = Math.sin(index * 1.73) * 1.55;

  return [
    Math.cos(angle) * radius,
    y,
    Math.sin(angle) * radius * 0.72,
  ];
}

export function ScanRadarScene({
  active,
  networkCount = 0,
  highRiskCount = 0,
}: ScanRadarSceneProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.set(0, 0.2, 8.8);

    let renderer: THREE.WebGLRenderer;

    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "low-power",
      });
    } catch {
      return undefined;
    }

    renderer.setClearColor(0x000000, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    host.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    const visibleCount = Math.min(Math.max(networkCount || 14, 10), 34);
    const positions: number[] = [0, 0, 0];
    const linePositions: number[] = [];

    for (let index = 0; index < visibleCount; index += 1) {
      const [x, y, z] = seededPoint(index, visibleCount);
      positions.push(x, y, z);
      linePositions.push(0, 0, 0, x, y, z);
    }

    const pointsGeometry = new THREE.BufferGeometry();
    pointsGeometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3),
    );

    const pointsMaterial = new THREE.PointsMaterial({
      color: 0xcbd4ff,
      size: 0.075,
      transparent: true,
      opacity: 0.92,
      sizeAttenuation: true,
    });

    const points = new THREE.Points(pointsGeometry, pointsMaterial);
    group.add(points);

    const lineGeometry = new THREE.BufferGeometry();
    lineGeometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(linePositions, 3),
    );

    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x8897e8,
      transparent: true,
      opacity: 0.15,
    });

    const lines = new THREE.LineSegments(lineGeometry, lineMaterial);
    group.add(lines);

    const coreGeometry = new THREE.SphereGeometry(0.16, 24, 24);
    const coreMaterial = new THREE.MeshBasicMaterial({ color: 0x2ac7a9 });
    const core = new THREE.Mesh(coreGeometry, coreMaterial);
    group.add(core);

    const ringGeometry = new THREE.RingGeometry(1.7, 1.72, 96);
    const ringMaterial = new THREE.MeshBasicMaterial({
      color: 0x7180d2,
      transparent: true,
      opacity: 0.17,
      side: THREE.DoubleSide,
    });
    const ring = new THREE.Mesh(ringGeometry, ringMaterial);
    ring.rotation.x = Math.PI / 2.38;
    ring.rotation.z = 0.12;
    group.add(ring);

    const outerRingGeometry = new THREE.RingGeometry(2.75, 2.765, 96);
    const outerRingMaterial = new THREE.MeshBasicMaterial({
      color: highRiskCount > 0 ? 0xf59e9e : 0x6578d7,
      transparent: true,
      opacity: highRiskCount > 0 ? 0.22 : 0.11,
      side: THREE.DoubleSide,
    });
    const outerRing = new THREE.Mesh(outerRingGeometry, outerRingMaterial);
    outerRing.rotation.x = Math.PI / 2.38;
    outerRing.rotation.z = 0.12;
    group.add(outerRing);

    const resize = () => {
      const width = Math.max(host.clientWidth, 1);
      const height = Math.max(host.clientHeight, 1);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
    };

    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();

    const tweens: gsap.core.Tween[] = [];

    if (!reducedMotion) {
      tweens.push(
        gsap.to(group.rotation, {
          y: active ? Math.PI * 2 : 0.3,
          duration: active ? 7.5 : 22,
          repeat: -1,
          ease: active ? "none" : "sine.inOut",
          yoyo: !active,
        }),
        gsap.to(core.scale, {
          x: active ? 1.55 : 1.18,
          y: active ? 1.55 : 1.18,
          z: active ? 1.55 : 1.18,
          duration: active ? 0.85 : 2.4,
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
        }),
        gsap.to(lineMaterial, {
          opacity: active ? 0.31 : 0.15,
          duration: active ? 0.9 : 2.2,
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
        }),
      );

      renderer.setAnimationLoop(() => renderer.render(scene, camera));
    }

    return () => {
      tweens.forEach((tween) => tween.kill());
      renderer.setAnimationLoop(null);
      observer.disconnect();
      pointsGeometry.dispose();
      pointsMaterial.dispose();
      lineGeometry.dispose();
      lineMaterial.dispose();
      coreGeometry.dispose();
      coreMaterial.dispose();
      ringGeometry.dispose();
      ringMaterial.dispose();
      outerRingGeometry.dispose();
      outerRingMaterial.dispose();
      renderer.dispose();

      if (renderer.domElement.parentElement === host) {
        host.removeChild(renderer.domElement);
      }
    };
  }, [active, highRiskCount, networkCount, reducedMotion]);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || reducedMotion) return undefined;

    const rings = Array.from(svg.querySelectorAll<SVGCircleElement>("[data-scan-ring]"));
    const sweep = svg.querySelector<SVGLineElement>("[data-scan-sweep]");

    const ringAnimations = rings.map((ring, index) =>
      animate(ring, {
        opacity: active ? [0.12, 0.4, 0.12] : [0.12, 0.22, 0.12],
        scale: active ? [0.92, 1.08, 0.92] : [0.98, 1.02, 0.98],
        duration: active ? 1800 + index * 240 : 4400 + index * 320,
        delay: index * 180,
        ease: "inOutSine",
        loop: true,
      }),
    );

    const sweepAnimation = sweep
      ? animate(sweep, {
          rotate: active ? [0, 360] : [0, 12, 0],
          duration: active ? 2600 : 9000,
          ease: active ? "linear" : "inOutSine",
          loop: true,
        })
      : null;

    return () => {
      ringAnimations.forEach((animation) => animation.cancel());
      sweepAnimation?.cancel();
    };
  }, [active, reducedMotion]);

  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      <div ref={hostRef} className="absolute inset-0 opacity-90" />

      <svg
        ref={svgRef}
        viewBox="0 0 500 500"
        className="absolute left-1/2 top-1/2 h-[88%] w-[88%] -translate-x-1/2 -translate-y-1/2 opacity-70"
      >
        <defs>
          <radialGradient id="scan-radar-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#2ac7a9" stopOpacity="0.16" />
            <stop offset="62%" stopColor="#7180d2" stopOpacity="0.04" />
            <stop offset="100%" stopColor="#7180d2" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="scan-sweep-gradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#2ac7a9" stopOpacity="0" />
            <stop offset="100%" stopColor="#2ac7a9" stopOpacity="0.8" />
          </linearGradient>
        </defs>

        <circle cx="250" cy="250" r="195" fill="url(#scan-radar-glow)" />
        {[76, 126, 176].map((radius) => (
          <circle
            key={radius}
            cx="250"
            cy="250"
            r={radius}
            fill="none"
            stroke="#b6c0ff"
            strokeWidth="1"
            opacity="0.14"
            data-scan-ring
            style={{ transformBox: "fill-box", transformOrigin: "center" }}
          />
        ))}
        <line x1="250" y1="250" x2="430" y2="250" stroke="url(#scan-sweep-gradient)" strokeWidth="1.4" data-scan-sweep style={{ transformBox: "fill-box", transformOrigin: "0% 50%" }} />
      </svg>

      <div className="absolute left-1/2 top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#2ac7a9] shadow-[0_0_0_8px_rgba(42,199,169,0.08),0_0_28px_rgba(42,199,169,0.55)]" />
    </div>
  );
}
