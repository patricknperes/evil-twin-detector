import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import * as THREE from "three";
import { animationTokens } from "../../lib/animation";

interface AmbientNetworkSceneProps {
  reducedMotion?: boolean;
}

const NETWORK_POINT_COUNT = 42;
const ACCENT_POINT_COUNT = 9;

function buildNetworkPositions(count: number): Float32Array {
  const values = new Float32Array(count * 3);

  for (let index = 0; index < count; index += 1) {
    const theta = index * 2.399963229728653;
    const radius = 2.5 + (index % 7) * 0.72;
    const wave = Math.sin(index * 0.83) * 1.45;

    values[index * 3] = Math.cos(theta) * radius + Math.sin(index * 0.37) * 1.15;
    values[index * 3 + 1] = Math.sin(theta) * radius * 0.62 + wave;
    values[index * 3 + 2] = Math.cos(index * 0.61) * 2.6;
  }

  return values;
}

function buildConnectionPositions(points: Float32Array): Float32Array {
  const segments: number[] = [];
  const pointCount = points.length / 3;

  for (let index = 0; index < pointCount; index += 1) {
    const nextIndex = (index + 5 + (index % 3)) % pointCount;
    const x1 = points[index * 3];
    const y1 = points[index * 3 + 1];
    const z1 = points[index * 3 + 2];
    const x2 = points[nextIndex * 3];
    const y2 = points[nextIndex * 3 + 1];
    const z2 = points[nextIndex * 3 + 2];
    const distance = Math.hypot(x2 - x1, y2 - y1, z2 - z1);

    if (distance < 7.4) {
      segments.push(x1, y1, z1, x2, y2, z2);
    }
  }

  return new Float32Array(segments);
}

export function AmbientNetworkScene({ reducedMotion = false }: AmbientNetworkSceneProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;

    let renderer: THREE.WebGLRenderer;

    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: "low-power",
      });
    } catch {
      return undefined;
    }

    renderer.setClearColor(0x000000, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.domElement.className = "h-full w-full";
    renderer.domElement.setAttribute("aria-hidden", "true");
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.set(0, 0, 17);

    const networkGroup = new THREE.Group();
    networkGroup.rotation.set(-0.16, -0.12, -0.08);
    networkGroup.position.set(2.3, -0.4, 0);
    scene.add(networkGroup);

    const networkPositions = buildNetworkPositions(NETWORK_POINT_COUNT);
    const pointGeometry = new THREE.BufferGeometry();
    pointGeometry.setAttribute("position", new THREE.BufferAttribute(networkPositions, 3));

    const pointMaterial = new THREE.PointsMaterial({
      color: 0x5366c6,
      opacity: reducedMotion ? 0.28 : 0,
      size: 0.11,
      sizeAttenuation: true,
      transparent: true,
      depthWrite: false,
    });
    const points = new THREE.Points(pointGeometry, pointMaterial);
    networkGroup.add(points);

    const accentGeometry = new THREE.BufferGeometry();
    const accentPositions = new Float32Array(ACCENT_POINT_COUNT * 3);
    for (let index = 0; index < ACCENT_POINT_COUNT; index += 1) {
      const sourceIndex = (index * 4 + 3) % NETWORK_POINT_COUNT;
      accentPositions[index * 3] = networkPositions[sourceIndex * 3];
      accentPositions[index * 3 + 1] = networkPositions[sourceIndex * 3 + 1];
      accentPositions[index * 3 + 2] = networkPositions[sourceIndex * 3 + 2];
    }
    accentGeometry.setAttribute("position", new THREE.BufferAttribute(accentPositions, 3));

    const accentMaterial = new THREE.PointsMaterial({
      color: 0x2ac7a9,
      opacity: reducedMotion ? 0.42 : 0,
      size: 0.16,
      sizeAttenuation: true,
      transparent: true,
      depthWrite: false,
    });
    const accentPoints = new THREE.Points(accentGeometry, accentMaterial);
    networkGroup.add(accentPoints);

    const lineGeometry = new THREE.BufferGeometry();
    lineGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(buildConnectionPositions(networkPositions), 3),
    );
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x7180d2,
      opacity: reducedMotion ? 0.08 : 0,
      transparent: true,
      depthWrite: false,
    });
    const connections = new THREE.LineSegments(lineGeometry, lineMaterial);
    networkGroup.add(connections);

    const resize = () => {
      const width = Math.max(host.clientWidth, 1);
      const height = Math.max(host.clientHeight, 1);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(host);
    resize();

    const tweens: gsap.core.Tween[] = [];
    let intro: gsap.core.Timeline | null = null;

    if (!reducedMotion) {
      intro = gsap.timeline({ defaults: { ease: animationTokens.gsapEase } });
      intro
        .to(lineMaterial, { opacity: 0.09, duration: 1.1 }, 0)
        .to(pointMaterial, { opacity: 0.34, duration: 1.25 }, 0.08)
        .to(accentMaterial, { opacity: 0.5, duration: 1.2 }, 0.2);

      tweens.push(
        gsap.to(networkGroup.rotation, {
          y: 0.18,
          x: -0.06,
          duration: 24,
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
        }),
        gsap.to(networkGroup.position, {
          y: 0.42,
          duration: 13,
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
        }),
      );

      renderer.setAnimationLoop(() => renderer.render(scene, camera));
    }

    return () => {
      intro?.kill();
      tweens.forEach((tween) => tween.kill());
      renderer.setAnimationLoop(null);
      resizeObserver.disconnect();

      pointGeometry.dispose();
      pointMaterial.dispose();
      accentGeometry.dispose();
      accentMaterial.dispose();
      lineGeometry.dispose();
      lineMaterial.dispose();
      renderer.dispose();

      if (renderer.domElement.parentElement === host) {
        host.removeChild(renderer.domElement);
      }
    };
  }, [reducedMotion]);

  return <div ref={hostRef} className="absolute inset-0" aria-hidden="true" />;
}
