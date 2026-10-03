import { useEffect, useRef } from "react";

/**
 * Dependency-free 3D particle field rendered to a fixed full-screen canvas.
 *
 * Particles live in a 3D box and drift toward the viewer; they're projected
 * with a real perspective divide (focal / z), so near points are larger and
 * brighter. The whole field rotates slightly toward the mouse for parallax.
 * Near particles are linked with faint lines for a "network" feel. Neon green
 * with occasional red, matching the gaming theme. Sits behind the UI
 * (z-index -1, pointer-events none) and honors prefers-reduced-motion.
 */
export function NeonField() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const DEPTH = 1000; // z range [1, DEPTH]
    const FOCAL = 520; // perspective focal length
    const COUNT = Math.min(
      170,
      Math.max(70, Math.floor((window.innerWidth * window.innerHeight) / 14000)),
    );

    type P = { x: number; y: number; z: number; red: boolean };
    const spread = 1400;
    const particles: P[] = Array.from({ length: COUNT }, () => ({
      x: (Math.random() - 0.5) * spread,
      y: (Math.random() - 0.5) * spread,
      z: Math.random() * DEPTH + 1,
      red: Math.random() < 0.12, // ~12% red accents, rest green
    }));

    let w = 0;
    let h = 0;
    let dpr = 1;
    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas!.width = Math.floor(w * dpr);
      canvas!.height = Math.floor(h * dpr);
      canvas!.style.width = w + "px";
      canvas!.style.height = h + "px";
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    // Mouse parallax: target rotation angles, eased each frame.
    let targetRX = 0;
    let targetRY = 0;
    let rx = 0;
    let ry = 0;
    function onMove(e: MouseEvent) {
      targetRY = (e.clientX / window.innerWidth - 0.5) * 0.6;
      targetRX = (e.clientY / window.innerHeight - 0.5) * 0.6;
    }
    window.addEventListener("mousemove", onMove);

    type Proj = { sx: number; sy: number; scale: number; red: boolean };

    function render() {
      rx += (targetRX - rx) * 0.05;
      ry += (targetRY - ry) * 0.05;
      const cosY = Math.cos(ry);
      const sinY = Math.sin(ry);
      const cosX = Math.cos(rx);
      const sinX = Math.sin(rx);

      ctx!.clearRect(0, 0, w, h);

      const proj: Proj[] = [];
      for (const p of particles) {
        if (!reduceMotion) {
          p.z -= 2.2;
          if (p.z < 1) {
            // recycle to the far plane with a fresh x/y
            p.z = DEPTH;
            p.x = (Math.random() - 0.5) * spread;
            p.y = (Math.random() - 0.5) * spread;
          }
        }

        // rotate around Y then X for mouse parallax
        let x = p.x * cosY - p.z * sinY;
        let z = p.x * sinY + p.z * cosY;
        let y = p.y * cosX - z * sinX;
        z = p.y * sinX + z * cosX;
        z += DEPTH * 0.15; // push forward so rotation never divides by ~0
        if (z < 1) continue;

        const scale = FOCAL / z;
        const sx = w / 2 + x * scale;
        const sy = h / 2 + y * scale;
        proj.push({ sx, sy, scale, red: p.red });

        const depth = Math.min(1, scale * 1.1); // 0 far .. ~1 near
        const r = Math.max(0.4, scale * 2.4);
        const alpha = 0.15 + depth * 0.7;
        ctx!.beginPath();
        ctx!.arc(sx, sy, r, 0, Math.PI * 2);
        ctx!.fillStyle = p.red
          ? `rgba(239, 68, 68, ${alpha})`
          : `rgba(34, 197, 94, ${alpha})`;
        ctx!.fill();
      }

      // Link nearby near-camera particles (cheap: only the closer ones).
      const near = proj.filter((q) => q.scale > FOCAL / (DEPTH * 0.55));
      const LINK = 130;
      for (let i = 0; i < near.length; i++) {
        for (let j = i + 1; j < near.length; j++) {
          const a = near[i];
          const b = near[j];
          const dx = a.sx - b.sx;
          const dy = a.sy - b.sy;
          const d2 = dx * dx + dy * dy;
          if (d2 < LINK * LINK) {
            const t = 1 - Math.sqrt(d2) / LINK;
            ctx!.strokeStyle = `rgba(34, 197, 94, ${t * 0.18})`;
            ctx!.lineWidth = 0.6;
            ctx!.beginPath();
            ctx!.moveTo(a.sx, a.sy);
            ctx!.lineTo(b.sx, b.sy);
            ctx!.stroke();
          }
        }
      }

      frame = requestAnimationFrame(render);
    }

    let frame = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10"
    />
  );
}
