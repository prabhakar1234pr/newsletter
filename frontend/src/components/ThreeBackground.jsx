import { useRef, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/* ── Particle field ────────────────────────────────────── */
function Particles({ count = 1800 }) {
  const mesh = useRef();
  const mouse = useRef({ x: 0, y: 0 });
  const { size } = useThree();

  // Generate particle positions
  const [positions, colors] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      // Spread across a wide plane
      pos[i * 3]     = (Math.random() - 0.5) * 28;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 16;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 8 - 2;

      // Color palette: indigo → violet → white
      const t = Math.random();
      if (t < 0.4) {
        col[i * 3]     = 0.38; col[i * 3 + 1] = 0.40; col[i * 3 + 2] = 0.95; // indigo
      } else if (t < 0.7) {
        col[i * 3]     = 0.55; col[i * 3 + 1] = 0.36; col[i * 3 + 2] = 0.96; // violet
      } else if (t < 0.9) {
        col[i * 3]     = 0.93; col[i * 3 + 1] = 0.28; col[i * 3 + 2] = 0.60; // pink
      } else {
        col[i * 3]     = 0.85; col[i * 3 + 1] = 0.85; col[i * 3 + 2] = 0.95; // white
      }
    }
    return [pos, col];
  }, [count]);

  // Track mouse
  useMemo(() => {
    const onMove = (e) => {
      mouse.current.x = (e.clientX / window.innerWidth  - 0.5) * 2;
      mouse.current.y = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  useFrame((state) => {
    const t = state.clock.elapsedTime;

    // Gentle drift + mouse parallax
    if (mesh.current) {
      mesh.current.rotation.y = t * 0.012 + mouse.current.x * 0.08;
      mesh.current.rotation.x = t * 0.006 - mouse.current.y * 0.04;
    }

    // Pulse opacity
    if (mesh.current?.material) {
      mesh.current.material.opacity = 0.55 + Math.sin(t * 0.4) * 0.08;
    }
  });

  return (
    <points ref={mesh}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color"    args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.045}
        vertexColors
        transparent
        opacity={0.6}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

/* ── Connecting lines ──────────────────────────────────── */
function ConnectionLines({ count = 120 }) {
  const ref = useRef();

  const geometry = useMemo(() => {
    const pts = [];
    for (let i = 0; i < count; i++) {
      const ax = (Math.random() - 0.5) * 22;
      const ay = (Math.random() - 0.5) * 12;
      const az = (Math.random() - 0.5) * 4 - 2;
      const bx = ax + (Math.random() - 0.5) * 5;
      const by = ay + (Math.random() - 0.5) * 3;
      const bz = az + (Math.random() - 0.5) * 1;
      pts.push(ax, ay, az, bx, by, bz);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    return g;
  }, [count]);

  useFrame((state) => {
    if (ref.current?.material) {
      ref.current.material.opacity = 0.08 + Math.sin(state.clock.elapsedTime * 0.3) * 0.03;
    }
  });

  return (
    <lineSegments ref={ref} geometry={geometry}>
      <lineBasicMaterial color="#6366F1" transparent opacity={0.1} depthWrite={false} />
    </lineSegments>
  );
}

/* ── Glowing orbs ──────────────────────────────────────── */
function GlowOrbs() {
  const orbs = useRef([]);

  const positions = useMemo(() => [
    [-4, 1, -3], [4, -1, -4], [0, 2, -5], [-6, -2, -6], [6, 1, -5],
  ], []);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    positions.forEach((_, i) => {
      if (orbs.current[i]) {
        orbs.current[i].position.y = positions[i][1] + Math.sin(t * 0.4 + i * 1.2) * 0.4;
        orbs.current[i].material.opacity = 0.06 + Math.sin(t * 0.5 + i * 0.8) * 0.03;
      }
    });
  });

  return (
    <>
      {positions.map((pos, i) => (
        <mesh
          key={i}
          ref={(el) => (orbs.current[i] = el)}
          position={pos}
        >
          <sphereGeometry args={[i % 2 === 0 ? 1.2 : 0.8, 16, 16]} />
          <meshBasicMaterial
            color={i % 3 === 0 ? "#6366F1" : i % 3 === 1 ? "#8B5CF6" : "#EC4899"}
            transparent
            opacity={0.07}
            depthWrite={false}
          />
        </mesh>
      ))}
    </>
  );
}

/* ── Export ────────────────────────────────────────────── */
export default function ThreeBackground({ className = "" }) {
  return (
    <div className={`absolute inset-0 ${className}`} style={{ pointerEvents: "none" }}>
      <Canvas
        camera={{ position: [0, 0, 8], fov: 65 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
        dpr={[1, 1.5]}
      >
        <GlowOrbs />
        <ConnectionLines count={100} />
        <Particles count={1600} />
      </Canvas>
    </div>
  );
}
