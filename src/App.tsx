import { useState, useEffect, useRef } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Header } from './components/Header';
import { ClaimInput } from './components/ClaimInput';
import { LoadingState } from './components/LoadingState';
import { ResultsView } from './components/ResultsView';
import { HistorySidebar } from './components/HistorySidebar';
import { TrustSection } from './components/TrustSection';
import { SciVerifyHeroLogo } from './components/SciVerifyHeroLogo';
import { AuthPage } from './components/AuthPage';
import { verifyClaimOnline } from './services/api';
import type { VerificationResult } from './services/mockVerification';

type BootPhase = 
  | 'BOOT_CHAOS' 
  | 'BOOT_GLOW'
  | 'BOOT_EMIT'
  | 'BOOT_COLLAPSE'
  | 'BOOT_VERIFICATION' 
  | 'BOOT_REVEAL'
  | 'BOOT_MORPH' 
  | 'READY';

// Drifting canvas with self-organizing molecular/orbital physics and premium animations
const BackgroundCanvas: React.FC<{ bootPhase: BootPhase; theme: 'light' | 'dark'; speedFactor?: number }> = ({ bootPhase, theme, speedFactor = 1 }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const shouldReduceMotion = useReducedMotion();
  const phaseStartRef = useRef<number>(Date.now());
  const prevPhaseRef = useRef<string>(bootPhase);

  // 1. Floating Molecules system (Molecular Flow & Bond Animation)
  const moleculesRef = useRef<Array<{
    x: number;
    y: number;
    vx: number;
    vy: number;
    angle: number;
    vAngle: number;
    size: number;
    atoms: Array<{ rx: number; ry: number; size: number; glowPhase: number; glowSpeed: number }>;
    bonds: Array<{ from: number; to: number }>;
    packets: Array<{ bondIndex: number; progress: number; speed: number }>;
  }>>([]);

  // 2. Floating Research Papers (bottom-left)
  const papersRef = useRef<Array<{
    baseX: number;
    baseY: number;
    w: number;
    h: number;
    anglePhase: number;
    floatPhase: number;
  }>>([]);

  // 3. Research Network (top-center neural graph)
  const networkRef = useRef<{
    nodes: Array<{ x: number; y: number; baseSize: number; pulsePhase: number; pulseSpeed: number }>;
    links: Array<{ from: number; to: number }>;
    packets: Array<{ from: number; to: number; progress: number; speed: number }>;
  }>({ nodes: [], links: [], packets: [] });

  useEffect(() => {
    if (bootPhase !== prevPhaseRef.current) {
      phaseStartRef.current = Date.now();
      prevPhaseRef.current = bootPhase;
    }
  }, [bootPhase]);

  useEffect(() => {
    if (shouldReduceMotion) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.offsetWidth);
    let height = (canvas.height = canvas.offsetHeight);

    // Initialize Molecules
    if (moleculesRef.current.length === 0) {
      moleculesRef.current = Array.from({ length: 6 }).map(() => {
        const numAtoms = 4 + Math.floor(Math.random() * 3);
        const atoms = Array.from({ length: numAtoms }).map(() => {
          return {
            rx: (Math.random() - 0.5) * 80,
            ry: (Math.random() - 0.5) * 80,
            size: Math.random() * 2.5 + 1.5,
            glowPhase: Math.random() * Math.PI * 2,
            glowSpeed: Math.random() * 0.02 + 0.01
          };
        });

        const bonds: Array<{ from: number; to: number }> = [];
        for (let i = 1; i < numAtoms; i++) {
          bonds.push({ from: i - 1, to: i });
        }
        if (numAtoms > 4) {
          bonds.push({ from: 0, to: numAtoms - 1 });
        }

        const packets = bonds.map((_, bIdx) => ({
          bondIndex: bIdx,
          progress: Math.random(),
          speed: Math.random() * 0.003 + 0.002
        }));

        return {
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.06 - 0.02, // 30-50px every 8-12 seconds
          vy: (Math.random() - 0.5) * 0.06 - 0.02,
          angle: Math.random() * Math.PI * 2,
          vAngle: (Math.random() - 0.5) * 0.0006, // extremely slow
          size: Math.random() * 0.3 + 0.85,
          atoms,
          bonds,
          packets
        };
      });
    }

    // Initialize Research Papers (bottom-left)
    if (papersRef.current.length === 0) {
      papersRef.current = [
        { baseX: 80, baseY: height - 140, w: 45, h: 60, anglePhase: 0, floatPhase: 0 },
        { baseX: 140, baseY: height - 90, w: 50, h: 40, anglePhase: Math.PI * 0.4, floatPhase: Math.PI * 0.6 },
        { baseX: 90, baseY: height - 80, w: 40, h: 50, anglePhase: Math.PI * 0.8, floatPhase: Math.PI * 1.2 }
      ];
    }

    // Initialize Neural Network (top-right data transmission)
    if (networkRef.current.nodes.length === 0) {
      const nodeCoords = [
        { x: width * 0.8, y: 110 },
        { x: width * 0.84, y: 70 },
        { x: width * 0.88, y: 120 },
        { x: width * 0.82, y: 150 },
        { x: width * 0.86, y: 140 },
        { x: width * 0.83, y: 95 },
        { x: width * 0.87, y: 80 }
      ];

      const nodes = nodeCoords.map((n) => ({
        x: n.x,
        y: n.y,
        baseSize: Math.random() * 2 + 1.5,
        pulsePhase: Math.random() * Math.PI * 2,
        pulseSpeed: Math.random() * 0.03 + 0.01
      }));

      const links = [
        { from: 0, to: 1 },
        { from: 1, to: 2 },
        { from: 2, to: 3 },
        { from: 3, to: 4 },
        { from: 1, to: 5 },
        { from: 5, to: 6 },
        { from: 6, to: 3 },
        { from: 0, to: 6 },
        { from: 2, to: 4 }
      ];

      const packets = Array.from({ length: 4 }).map(() => {
        const link = links[Math.floor(Math.random() * links.length)];
        return {
          from: link.from,
          to: link.to,
          progress: Math.random(),
          speed: Math.random() * 0.006 + 0.004
        };
      });

      networkRef.current = { nodes, links, packets };
    }

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;

      // Adjust network layout proportionally
      if (networkRef.current.nodes.length > 0) {
        const coords = [
          { x: width * 0.8, y: 110 },
          { x: width * 0.84, y: 70 },
          { x: width * 0.88, y: 120 },
          { x: width * 0.82, y: 150 },
          { x: width * 0.86, y: 140 },
          { x: width * 0.83, y: 95 },
          { x: width * 0.87, y: 80 }
        ];
        networkRef.current.nodes.forEach((n, idx) => {
          n.x = coords[idx].x;
          n.y = coords[idx].y;
        });
      }

      // Re-align paper base coordinates
      if (papersRef.current.length > 0) {
        papersRef.current[0].baseY = height - 140;
        papersRef.current[1].baseY = height - 90;
        papersRef.current[2].baseY = height - 80;
      }
    };
    window.addEventListener('resize', handleResize);

    const render = () => {
      ctx.clearRect(0, 0, width, height);
      
      const time = Date.now();
      const speedScale = speedFactor;
      const isDark = theme === 'dark';

      // Theme-aware dynamic canvas colors
      const nodeColor = (alpha: number) => isDark ? `rgba(255, 255, 255, ${alpha})` : `rgba(15, 23, 42, ${alpha * 0.95})`;
      const linkColor = (alpha: number) => isDark ? `rgba(255, 255, 255, ${alpha})` : `rgba(71, 85, 105, ${alpha * 0.95})`;
      const blueColor = (alpha: number) => isDark ? `rgba(59, 130, 246, ${alpha})` : `rgba(37, 99, 235, ${alpha})`;

      // --- 1. DNA HELIX (Right Side scrolling & shimmer) ---
      const dnaCx = width * 0.92;
      const dnaAmp = 25;
      const dnaPhase = time * 0.0018 * speedScale;
      const dnaShimmerY = (time * 0.06) % (height * 2) - height / 2;

      ctx.beginPath();
      for (let y = 30; y < height - 30; y += 2) {
        const x1 = dnaCx + Math.sin(y * 0.008 + dnaPhase) * dnaAmp;
        const x2 = dnaCx - Math.sin(y * 0.008 + dnaPhase) * dnaAmp;

        // Base pairs horizontal lines
        if (Math.floor(y) % 22 === 0) {
          const isShimmer = Math.abs(y - dnaShimmerY) < 100;
          let linkAlpha = isShimmer ? 0.28 : 0.06;
          
          ctx.strokeStyle = blueColor(linkAlpha * speedScale);
          ctx.lineWidth = isShimmer ? 1.0 : 0.5;
          ctx.beginPath();
          ctx.moveTo(x1, y);
          ctx.lineTo(x2, y);
          ctx.stroke();

          // Shimmer glow packets
          if (isShimmer && Math.floor(y) % 44 === 0) {
            ctx.fillStyle = isDark ? 'rgba(255, 255, 255, 0.45)' : 'rgba(15, 23, 42, 0.4)';
            ctx.beginPath();
            ctx.arc(x1 + (x2 - x1) * 0.5, y, 1.2, 0, Math.PI * 2);
            ctx.fill();
          }
        }

        // Backbone nodes
        if (Math.floor(y) % 6 === 0) {
          const isShimmer = Math.abs(y - dnaShimmerY) < 100;
          ctx.fillStyle = isDark ? (isShimmer ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.06)') : (isShimmer ? 'rgba(15, 23, 42, 0.2)' : 'rgba(15, 23, 42, 0.05)');
          
          ctx.beginPath();
          ctx.arc(x1, y, isShimmer ? 1.5 : 1.0, 0, Math.PI * 2);
          ctx.arc(x2, y, isShimmer ? 1.5 : 1.0, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // --- 2. FLOATING RESEARCH PAPERS (bottom-left) ---
      papersRef.current.forEach((p) => {
        p.anglePhase += 0.0035 * speedScale;
        p.floatPhase += 0.0045 * speedScale;

        const floatY = Math.sin(p.floatPhase) * 6;
        const floatX = Math.cos(p.floatPhase * 0.8) * 3;
        const angle = Math.sin(p.anglePhase) * (2 * Math.PI / 180); // ±2 degrees

        ctx.save();
        ctx.translate(p.baseX + floatX, p.baseY + floatY);
        ctx.rotate(angle);

        // Draw document board card borders
        ctx.strokeStyle = nodeColor(0.015);
        ctx.lineWidth = 0.8;
        ctx.fillStyle = nodeColor(0.002);
        ctx.beginPath();
        ctx.rect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.fill();
        ctx.stroke();

        // Draw horizontal line lines to match chart text
        ctx.strokeStyle = linkColor(0.008);
        ctx.lineWidth = 0.5;
        for (let ly = -p.h / 2 + 8; ly < p.h / 2 - 4; ly += 6) {
          ctx.beginPath();
          ctx.moveTo(-p.w / 2 + 6, ly);
          ctx.lineTo(p.w / 2 - 6, ly);
          ctx.stroke();
        }

        ctx.restore();
      });

      // --- 3. RESEARCH NETWORK (top-center data) ---
      const net = networkRef.current;
      
      // Update nodes pulse
      net.nodes.forEach((n) => {
        n.pulsePhase += n.pulseSpeed * speedScale;
      });

      // Draw links
      ctx.beginPath();
      net.links.forEach((l) => {
        const n1 = net.nodes[l.from];
        const n2 = net.nodes[l.to];
        ctx.strokeStyle = linkColor(0.012);
        ctx.lineWidth = 0.5;
        ctx.moveTo(n1.x, n1.y);
        ctx.lineTo(n2.x, n2.y);
      });
      ctx.stroke();

      // Draw nodes
      net.nodes.forEach((n) => {
        const scale = 1 + Math.sin(n.pulsePhase) * 0.15;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.baseSize * scale, 0, Math.PI * 2);
        ctx.fillStyle = nodeColor(0.05 + Math.sin(n.pulsePhase) * 0.03);
        ctx.fill();
      });

      // Update & Draw packets
      net.packets.forEach((pk) => {
        pk.progress += pk.speed * speedScale;
        if (pk.progress >= 1) {
          pk.progress = 0;
          const linkedLinks = net.links.filter(l => l.from === pk.to || l.to === pk.to);
          if (linkedLinks.length > 0) {
            const nextLink = linkedLinks[Math.floor(Math.random() * linkedLinks.length)];
            pk.from = pk.to;
            pk.to = nextLink.from === pk.to ? nextLink.to : nextLink.from;
          }
        }

        const n1 = net.nodes[pk.from];
        const n2 = net.nodes[pk.to];
        const px = n1.x + (n2.x - n1.x) * pk.progress;
        const py = n1.y + (n2.y - n1.y) * pk.progress;

        ctx.fillStyle = isDark ? 'rgba(255, 255, 255, 0.35)' : 'rgba(15, 23, 42, 0.3)';
        ctx.beginPath();
        ctx.arc(px, py, 1.0, 0, Math.PI * 2);
        ctx.fill();
      });

      // --- 4. MOLECULAR FLOW (drifting particles & bonds) ---
      moleculesRef.current.forEach((m) => {
        m.x += m.vx * speedScale;
        m.y += m.vy * speedScale;
        m.angle += m.vAngle * speedScale;

        // Wrap boundaries
        if (m.x < -100) m.x = width + 100;
        if (m.x > width + 100) m.x = -100;
        if (m.y < -100) m.y = height + 100;
        if (m.y > height + 100) m.y = -100;

        // Opacity fade threshold
        const edgeThreshold = 100;
        let opacity = 1;
        if (m.x < edgeThreshold) opacity = Math.min(opacity, m.x / edgeThreshold);
        if (m.x > width - edgeThreshold) opacity = Math.min(opacity, (width - m.x) / edgeThreshold);
        if (m.y < edgeThreshold) opacity = Math.min(opacity, m.y / edgeThreshold);
        if (m.y > height - edgeThreshold) opacity = Math.min(opacity, (height - m.y) / edgeThreshold);
        opacity = Math.max(0, opacity);

        if (opacity <= 0) return;

        ctx.save();
        ctx.translate(m.x, m.y);
        ctx.rotate(m.angle);
        ctx.scale(m.size, m.size);

        // Draw Bonds
        m.bonds.forEach((b) => {
          const a1 = m.atoms[b.from];
          const a2 = m.atoms[b.to];

          const pulseAlpha = Math.sin(time * 0.0015 + b.from) * 0.015 + 0.025;
          ctx.strokeStyle = linkColor(pulseAlpha * opacity);
          ctx.lineWidth = 0.6;
          ctx.beginPath();
          ctx.moveTo(a1.rx, a1.ry);
          ctx.lineTo(a2.rx, a2.ry);
          ctx.stroke();
        });

        // Draw Travelling Light packets along bonds
        m.packets.forEach((pk) => {
          pk.progress += pk.speed * speedScale;
          if (pk.progress >= 1) pk.progress = 0;

          const b = m.bonds[pk.bondIndex];
          const a1 = m.atoms[b.from];
          const a2 = m.atoms[b.to];

          const px = a1.rx + (a2.rx - a1.rx) * pk.progress;
          const py = a1.ry + (a2.ry - a1.ry) * pk.progress;

          ctx.fillStyle = nodeColor(0.45 * opacity);
          ctx.beginPath();
          ctx.arc(px, py, 0.9, 0, Math.PI * 2);
          ctx.fill();
        });

        // Draw Atoms
        m.atoms.forEach((a) => {
          a.glowPhase += a.glowSpeed * speedScale;
          const glow = Math.sin(a.glowPhase) * 0.4 + 0.6;
          
          ctx.beginPath();
          ctx.arc(a.rx, a.ry, a.size, 0, Math.PI * 2);
          ctx.fillStyle = nodeColor((0.05 + glow * 0.06) * opacity * speedScale);
          ctx.fill();
          
          ctx.strokeStyle = nodeColor((0.02 + glow * 0.03) * opacity * speedScale);
          ctx.lineWidth = 0.5;
          ctx.stroke();
        });

        ctx.restore();
      });

      // --- 5. SWAYING VOLUMETRIC RAY EFFECT ---
      const glowX = width / 2 + Math.sin(time * 0.00015) * 60;
      const glowY = height * 0.4 + Math.cos(time * 0.0002) * 40;
      
      const glowGrad = ctx.createRadialGradient(
        glowX, glowY, 50, 
        glowX, glowY, 350
      );
      glowGrad.addColorStop(0, isDark ? 'rgba(59, 130, 246, 0.015)' : 'rgba(37, 99, 235, 0.012)');
      glowGrad.addColorStop(0.5, isDark ? 'rgba(59, 130, 246, 0.003)' : 'rgba(37, 99, 235, 0.002)');
      glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      
      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(glowX, glowY, 350, 0, Math.PI * 2);
      ctx.fill();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [shouldReduceMotion, speedFactor, theme]);

  if (shouldReduceMotion) return null;
  return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none block z-10" />;
};

function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('sciverify_theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return 'dark'; // signature dark mode by default
  });
  const [bootPhase, setBootPhase] = useState<BootPhase>(() => {
    const booted = sessionStorage.getItem('sciverify_booted');
    return booted ? 'READY' : 'BOOT_CHAOS';
  });
  const [isBooting, setIsBooting] = useState(() => {
    const booted = sessionStorage.getItem('sciverify_booted');
    return !booted;
  });
  const [claim, setClaim] = useState('');
  const [selectedEngine, setSelectedEngine] = useState<'groq' | 'gemini' | 'compare'>('groq');
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [historyList, setHistoryList] = useState<VerificationResult[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isInputActive, setIsInputActive] = useState(false);

  // Authentication State
  const [currentUser, setCurrentUser] = useState<{ name: string; email: string; institution: string } | null>(() => {
    const stored = localStorage.getItem('sciverify_user');
    return stored ? JSON.parse(stored) : null;
  });
  const [authView, setAuthView] = useState<'login' | 'signup' | null>(null);

  // Parallax mouse tracker state
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = (e.clientY / window.innerHeight) * 2 - 1;
      setMousePos({ x, y });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const handleAuthSuccess = (user: { name: string; email: string; institution: string }) => {
    setCurrentUser(user);
    localStorage.setItem('sciverify_user', JSON.stringify(user));
    setAuthView(null);
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem('sciverify_user');
    setAuthView(null);
  };

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
    localStorage.setItem('sciverify_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const shouldReduceMotion = useReducedMotion();

  // Fail-safe backup timer (Overlay dims and vanishes within 5.5s max under any condition)
  useEffect(() => {
    if (shouldReduceMotion) {
      setBootPhase('READY');
      setIsBooting(false);
      return;
    }

    const failsafe = setTimeout(() => {
      setBootPhase('READY');
      setIsBooting(false);
    }, 5500);

    return () => clearTimeout(failsafe);
  }, [shouldReduceMotion]);

  // Boot sequence timelines (0ms -> 3600ms morph -> 4200ms ready)
  useEffect(() => {
    if (shouldReduceMotion || bootPhase === 'READY') return;

    const t1 = setTimeout(() => setBootPhase('BOOT_MORPH'), 3600);
    const t2 = setTimeout(() => {
      sessionStorage.setItem('sciverify_booted', 'true');
      setBootPhase('READY');
      setIsBooting(false);
    }, 4200);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [bootPhase, shouldReduceMotion]);

  // Load history cache on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('sciverify_history');
      if (stored) {
        setHistoryList(JSON.parse(stored));
      }
    } catch (e) {
      console.error('Failed to parse history from localStorage', e);
    }
  }, []);

  const handleVerify = (newClaim: string, engine: 'groq' | 'gemini' | 'compare' = 'groq') => {
    setClaim(newClaim);
    setSelectedEngine(engine);
    setBootPhase('READY');
    setIsBooting(false);
  };

  const handleLoadingComplete = async () => {
    const freshResult = await verifyClaimOnline(claim, selectedEngine);
    setResult(freshResult);
    
    setHistoryList(prev => {
      const updated = [freshResult, ...prev.filter(item => item.claim !== freshResult.claim)].slice(0, 10);
      localStorage.setItem('sciverify_history', JSON.stringify(updated));
      return updated;
    });

    setBootPhase('READY');
    setIsBooting(false);
  };

  const handleReset = () => {
    setClaim('');
    setResult(null);
  };

  const handleSelectHistory = (selectedResult: VerificationResult) => {
    setClaim(selectedResult.claim);
    setResult(selectedResult);
  };

  const handleClearHistory = () => {
    setHistoryList([]);
    localStorage.removeItem('sciverify_history');
  };

  // Stagger entry configurations
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: shouldReduceMotion ? 0 : 0.08,
        delayChildren: shouldReduceMotion ? 0 : 0.04
      }
    }
  };

  const itemVariants: any = {
    hidden: { opacity: 0, y: shouldReduceMotion ? 0 : 8 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.45,
        ease: [0.16, 1, 0.3, 1]
      }
    }
  };

  return (
    <motion.div 
      className="min-h-screen flex flex-col bg-paper text-ink selection:bg-blue-500/25 selection:text-blue-100 font-sans transition-colors duration-300 relative overflow-hidden"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Premium Animated Scientific Background (Loaded immediately on landing/boot) */}
      {claim === '' && (
        <div className="fixed inset-0 w-full h-full z-0 overflow-hidden pointer-events-none select-none">
          
          {/* Layer 1: Background Image (Base Layer - moves slightly less) */}
          <div 
            className="absolute inset-[-5%] w-[110%] h-[110%]"
            style={{ 
              animation: 'slowCameraDrift 38s infinite ease-in-out',
              willChange: 'transform'
            }}
          >
            <div 
              className="w-full h-full bg-cover bg-center bg-no-repeat transition-transform duration-1000 ease-out"
              style={{ 
                backgroundImage: theme === 'dark' ? 'url(/src/assets/hero.png)' : 'url(/src/assets/hero_light.png)',
                transform: `translate3d(${mousePos.x * 5}px, ${mousePos.y * 3}px, 0)`
              }}
            />
          </div>

          {/* Layer 2: Foreground Illustration Layer (moves slightly more, blended appropriately) */}
          <div 
            className="absolute inset-[-5%] w-[110%] h-[110%]"
            style={{ 
              animation: 'slowCameraDriftForeground 30s infinite ease-in-out',
              willChange: 'transform'
            }}
          >
            <div 
              className={`w-full h-full bg-cover bg-center bg-no-repeat transition-transform duration-700 ease-out ${
                theme === 'dark' ? 'mix-blend-screen opacity-[0.22]' : 'mix-blend-multiply opacity-[0.16]'
              }`}
              style={{ 
                backgroundImage: theme === 'dark' ? 'url(/src/assets/hero.png)' : 'url(/src/assets/hero_light.png)',
                transform: `translate3d(${mousePos.x * 15}px, ${mousePos.y * 8}px, 0)`
              }}
            />
          </div>

          {/* Layer 5: Microscope/Lab Equipment Diagonal Light Sweep Overlay (upper/bottom right) */}
          <div className="absolute right-0 top-0 bottom-0 w-[500px] overflow-hidden opacity-25 pointer-events-none select-none">
            <div 
              className="absolute w-[200%] h-[30%] bg-gradient-to-b from-transparent via-white/[0.04] to-transparent"
              style={{
                transform: 'rotate(35deg)',
                animation: 'microscopeSweep 14s infinite ease-in-out'
              }}
            />
          </div>

          {/* Layer 3: Soft Radial Vignette Overlay (Adjusted dark overlay 10-15% in center) */}
          <div className="absolute inset-0 bg-radial-vignette opacity-85" />

          {/* Layer 4: Animated scientific canvas (glowing dots, lines, floating molecules, scrolling helix) */}
          <BackgroundCanvas bootPhase={bootPhase} theme={theme} speedFactor={isInputActive ? 0.25 : 1} />
        </div>
      )}

      {/* Grid Pattern overlay lines */}
      <div className="grid-perspective-container opacity-25">
        <div className="scientific-grid-3d opacity-100 scientific-grid-animate" />
      </div>
 
      {/* Full-screen boot overlay sequence */}
      {isBooting && (
        <div 
          className={`fixed inset-0 bg-paper dark:bg-[#030712]/95 flex flex-col items-center justify-center z-50 select-none overflow-hidden transition-all duration-600 ${
            bootPhase === 'BOOT_MORPH' ? 'opacity-0 pointer-events-none' : 'opacity-100'
          }`}
        >
          {/* Faint 3D grid layout inside the boot overlay */}
          <div className="grid-perspective-container opacity-45">
            <div className="scientific-grid-3d opacity-100" />
          </div>
 
          {/* Redesigned SciVerify hero logo */}
          {bootPhase !== 'BOOT_MORPH' && bootPhase !== 'READY' && (
            <SciVerifyHeroLogo variant="boot" layoutId="main-logo-container" className="z-10" />
          )}
        </div>
      )}

      {/* Top Navbar Header (Logo morphs in during boot morph) */}
      {(bootPhase === 'BOOT_MORPH' || bootPhase === 'READY') && (
        <motion.div 
          variants={itemVariants} 
          className={`relative z-10 transition-opacity duration-500 ${
            isInputActive ? 'opacity-25' : 'opacity-100'
          }`}
        >
          <Header 
            onToggleHistory={() => setIsHistoryOpen(prev => !prev)} 
            historyCount={historyList.length} 
            theme={theme}
            onToggleTheme={toggleTheme}
            onLogoClick={handleReset}
            currentUser={currentUser}
            onOpenLogin={() => setAuthView('login')}
            onOpenSignup={() => setAuthView('signup')}
            onLogout={handleLogout}
          />
        </motion.div>
      )}

      {/* Main scientific viewport or Auth Page */}
      {authView !== null ? (
        <AuthPage 
          initialTab={authView}
          onAuthSuccess={handleAuthSuccess}
          onCancel={() => setAuthView(null)}
        />
      ) : (
        <>
          <main 
            className={`flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 relative z-10 transition-all duration-700 ${
              isBooting ? 'opacity-0 translate-y-12' : 'opacity-100 translate-y-0'
            }`}
          >
            {claim === '' && !result ? (
              <div className="space-y-16">
                
                {/* Centered Hero Header */}
                <motion.div 
                  variants={itemVariants} 
                  className={`text-center space-y-4 max-w-2xl mx-auto transition-opacity duration-500 ${
                    isInputActive ? 'opacity-15' : 'opacity-100'
                  }`}
                >
                  <h1 className="font-serif text-5xl font-extrabold tracking-tight text-ink md:text-6xl select-none">
                    SciVerify
                  </h1>
                  <p className="text-sm md:text-base text-slate-400 font-medium leading-relaxed max-w-lg mx-auto">
                    Verify scientific claims using evidence from peer-reviewed research.
                  </p>
                </motion.div>

                <motion.div variants={itemVariants}>
                  <ClaimInput onVerify={handleVerify} onFocusChange={setIsInputActive} currentUser={currentUser} />
                </motion.div>
                
                <motion.div 
                  variants={itemVariants}
                  className={`transition-opacity duration-500 ${isInputActive ? 'opacity-10' : 'opacity-100'}`}
                >
                  <TrustSection />
                </motion.div>
              </div>
            ) : claim !== '' && !result ? (
              <LoadingState claim={claim} onComplete={handleLoadingComplete} />
            ) : result ? (
              <ResultsView result={result} onReset={handleReset} />
            ) : null}
          </main>

          {/* Technical instrument footer */}
          <motion.footer 
            className={`w-full border-t border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-[#05070c] py-8 mt-24 text-[10px] font-mono tracking-wider text-slate-500 relative z-10 transition-opacity duration-500 ${
              isBooting 
                ? 'opacity-0 pointer-events-none' 
                : isInputActive 
                  ? 'opacity-10' 
                  : 'opacity-100'
            }`}
            variants={itemVariants}
          >
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <p>© {new Date().getFullYear()} SCIVERIFY CORE INFERENCE LAB</p>
              <div className="flex justify-center gap-6">
                <a href="#" className="hover:text-slate-300 transition-colors">PRIVACY_CODE</a>
                <a href="#" className="hover:text-slate-300 transition-colors">CORPUS_AGREEMENT</a>
                <a href="mailto:support@sciverify.edu" className="hover:text-slate-300 transition-colors">COMMUNICATIONS</a>
              </div>
            </div>
          </motion.footer>
        </>
      )}

      {/* Drawer for History ledger */}
      <HistorySidebar
        historyList={historyList}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelect={handleSelectHistory}
        onClear={handleClearHistory}
      />
    </motion.div>
  );
}

export default App;
