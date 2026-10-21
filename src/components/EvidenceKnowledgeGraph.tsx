import React, { useState, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Network, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  ExternalLink, 
  CheckCircle2, 
  XCircle, 
  Sparkles,
  Maximize2,
  Minimize2
} from 'lucide-react';
import type { VerificationResult, Verdict } from '../services/mockVerification';

export interface GraphNode {
  id: string;
  type: 'claim' | 'paper' | 'finding' | 'concept';
  label: string;
  sublabel?: string;
  verdict?: Verdict;
  confidence?: number;
  data?: any;
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  radius: number;
  color: string;
  borderColor: string;
  textColor: string;
  glowColor: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: 'SUPPORTS' | 'CONTRADICTS' | 'INSUFFICIENT' | 'EXTRACTS' | 'CORROBORATES' | 'CONTESTS' | 'RELATES_TO';
  label: string;
  weight?: number;
  dashed?: boolean;
  color: string;
}

interface EvidenceKnowledgeGraphProps {
  result: VerificationResult;
}

export const EvidenceKnowledgeGraph: React.FC<EvidenceKnowledgeGraphProps> = ({ result }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [filterStance, setFilterStance] = useState<'ALL' | 'SUPPORT' | 'CONTRADICT' | 'CONSENSUS'>('ALL');
  const [layoutMode, setLayoutMode] = useState<'radial' | 'bipartite' | 'hierarchical'>('radial');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDraggingCanvas, setIsDraggingCanvas] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Dragging individual nodes
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);
  const [nodeCustomPositions, setNodeCustomPositions] = useState<Record<string, { x: number; y: number }>>({});

  // Helper colors
  const getColorForVerdict = (v?: Verdict) => {
    switch (v) {
      case 'SUPPORT':
        return {
          bg: '#064e3b',
          border: '#10b981',
          text: '#6ee7b7',
          glow: 'rgba(16, 185, 129, 0.45)',
          edge: '#10b981'
        };
      case 'CONTRADICT':
        return {
          bg: '#7f1d1d',
          border: '#ef4444',
          text: '#fca5a5',
          glow: 'rgba(239, 68, 68, 0.45)',
          edge: '#ef4444'
        };
      case 'NOT ENOUGH INFO':
      default:
        return {
          bg: '#78350f',
          border: '#f59e0b',
          text: '#fde68a',
          glow: 'rgba(245, 158, 11, 0.45)',
          edge: '#f59e0b'
        };
    }
  };

  // Extract key concept keywords from claim & evidence
  const extractedConcepts = useMemo(() => {
    const claimWords = result.claim
      .replace(/[^\w\s-]/g, '')
      .split(/\s+/)
      .filter(w => w.length > 4 && !['reduces', 'causes', 'increases', 'effects', 'associated', 'between', 'during', 'treatment', 'versus', 'without'].includes(w.toLowerCase()));
    
    // Pick top 2-3 prominent terms
    const terms = Array.from(new Set(claimWords.map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()))).slice(0, 3);
    if (terms.length === 0) {
      terms.push('Clinical Outcome', 'Biomedical Mechanism');
    }
    return terms;
  }, [result.claim]);

  // Construct Nodes and Edges
  const { nodes, edges } = useMemo(() => {
    const nList: GraphNode[] = [];
    const eList: GraphEdge[] = [];

    const width = 850;
    const height = 550;
    const centerX = width / 2;
    const centerY = height / 2;

    const claimColors = getColorForVerdict(result.verdict);

    // 1. Central Claim Node
    const claimNode: GraphNode = {
      id: 'node-claim',
      type: 'claim',
      label: result.claim.length > 60 ? result.claim.slice(0, 57) + '...' : result.claim,
      sublabel: `TARGET CLAIM • VERDICT: ${result.verdict}`,
      verdict: result.verdict,
      confidence: result.confidence,
      data: {
        claim: result.claim,
        verdict: result.verdict,
        confidence: result.confidence,
        explanation: result.explanation,
        provenance: result.provenance
      },
      x: centerX,
      y: centerY,
      radius: 46,
      color: claimColors.bg,
      borderColor: claimColors.border,
      textColor: claimColors.text,
      glowColor: claimColors.glow
    };
    nList.push(claimNode);

    // 2. Concept Nodes (Orbiting closely)
    extractedConcepts.forEach((concept, cIdx) => {
      const cAngle = (cIdx / Math.max(1, extractedConcepts.length)) * Math.PI * 2 - Math.PI / 2;
      const cDist = 115;
      const cId = `node-concept-${cIdx}`;
      const cNode: GraphNode = {
        id: cId,
        type: 'concept',
        label: concept,
        sublabel: 'BIOMEDICAL DOMAIN',
        x: centerX + Math.cos(cAngle) * cDist,
        y: centerY + Math.sin(cAngle) * cDist,
        radius: 26,
        color: '#1e1b4b',
        borderColor: '#818cf8',
        textColor: '#c7d2fe',
        glowColor: 'rgba(129, 140, 248, 0.35)',
        data: {
          conceptName: concept,
          description: `Key biomedical entity or clinical endpoint grounded across the claim and indexed trials.`
        }
      };
      nList.push(cNode);

      // Edge from concept to claim
      eList.push({
        id: `edge-${cId}-claim`,
        source: cId,
        target: 'node-claim',
        type: 'RELATES_TO',
        label: 'CONCEPT',
        dashed: true,
        color: 'rgba(129, 140, 248, 0.45)'
      });
    });

    const papers = result.evidence || [];
    const paperCount = papers.length;

    // Fallback: If 0 papers (e.g. provisional model-knowledge assessment), synthesize mechanism & qualifications
    if (paperCount === 0) {
      if (result.scientificReasoning) {
        const synthId = 'node-synth-mech';
        nList.push({
          id: synthId,
          type: 'paper',
          label: 'Biological Mechanism Synthesis',
          sublabel: 'PRE-TRAINED EVIDENCE SYNTHESIS',
          verdict: result.verdict,
          confidence: result.confidence,
          data: {
            title: 'Biological Mechanism & Literature Synthesis',
            journal: 'Pre-Trained Scientific Literature',
            year: 2024,
            authors: result.verifiedBy || 'Inference Engine',
            abstract: result.scientificReasoning,
            highlightedSentence: result.scientificReasoning.slice(0, 140) + '...',
            link: `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(result.claim)}`
          },
          x: centerX - 180,
          y: centerY + 120,
          radius: 34,
          color: claimColors.bg,
          borderColor: claimColors.border,
          textColor: claimColors.text,
          glowColor: claimColors.glow
        });
        eList.push({
          id: `edge-${synthId}-claim`,
          source: synthId,
          target: 'node-claim',
          type: result.verdict === 'SUPPORT' ? 'SUPPORTS' : result.verdict === 'CONTRADICT' ? 'CONTRADICTS' : 'INSUFFICIENT',
          label: `MECHANISM (${result.confidence}%)`,
          weight: result.confidence,
          dashed: true,
          color: claimColors.border
        });
      }

      if (result.qualifications) {
        const qualId = 'node-qual-limit';
        nList.push({
          id: qualId,
          type: 'finding',
          label: 'Clinical Qualifications & Limitations',
          sublabel: 'EPIDEMIOLOGICAL BOUNDARIES',
          verdict: 'NOT ENOUGH INFO',
          confidence: 70,
          data: {
            parentPaperTitle: 'Clinical Trial Qualifications',
            sentence: result.qualifications,
            verdict: 'NOT ENOUGH INFO'
          },
          x: centerX + 180,
          y: centerY + 120,
          radius: 28,
          color: '#78350f',
          borderColor: '#f59e0b',
          textColor: '#fde68a',
          glowColor: 'rgba(245, 158, 11, 0.45)'
        });
        eList.push({
          id: `edge-${qualId}-claim`,
          source: qualId,
          target: 'node-claim',
          type: 'INSUFFICIENT',
          label: 'LIMITATIONS',
          dashed: true,
          color: '#f59e0b'
        });
      }
    }

    // 3. Research Paper Nodes & Finding Nodes
    papers.forEach((card, idx) => {
      const cardColors = getColorForVerdict(card.verdictContribution);
      let px = centerX;
      let py = centerY;

      if (layoutMode === 'radial') {
        // Radial arrangement around claim
        const angle = (idx / Math.max(1, paperCount)) * Math.PI * 2 - Math.PI / 4;
        const radius = 220;
        px = centerX + Math.cos(angle) * radius;
        py = centerY + Math.sin(angle) * radius;
      } else if (layoutMode === 'bipartite') {
        // Split: Supporting on Left, Contradicting on Right, Neutral in Center
        const isSupport = card.verdictContribution === 'SUPPORT';
        const isContradict = card.verdictContribution === 'CONTRADICT';
        const colX = isSupport ? centerX - 250 : isContradict ? centerX + 250 : centerX;
        const rowSpacing = 360 / Math.max(1, paperCount);
        px = colX;
        py = centerY - 150 + idx * rowSpacing;
      } else {
        // Hierarchical arrangement
        const colSpacing = 680 / Math.max(1, paperCount + 1);
        px = 85 + (idx + 1) * colSpacing;
        py = centerY + 180;
      }

      const paperNodeId = `node-paper-${card.id}`;
      const paperNode: GraphNode = {
        id: paperNodeId,
        type: 'paper',
        label: `[REF-${(idx + 1).toString().padStart(2, '0')}] ${card.title.slice(0, 36)}...`,
        sublabel: `${card.journal || 'Journal'} • ${card.year || '2021'}`,
        verdict: card.verdictContribution,
        confidence: card.confidence,
        data: card,
        x: px,
        y: py,
        radius: 34,
        color: cardColors.bg,
        borderColor: cardColors.border,
        textColor: cardColors.text,
        glowColor: cardColors.glow
      };
      nList.push(paperNode);

      // Edge from Paper to Claim (Verification link)
      eList.push({
        id: `edge-${paperNodeId}-claim`,
        source: paperNodeId,
        target: 'node-claim',
        type: card.verdictContribution === 'SUPPORT' ? 'SUPPORTS' : card.verdictContribution === 'CONTRADICT' ? 'CONTRADICTS' : 'INSUFFICIENT',
        label: `${card.verdictContribution === 'SUPPORT' ? 'SUPPORTS' : card.verdictContribution === 'CONTRADICT' ? 'REFUTES' : 'NEUTRAL'} (${card.confidence}%)`,
        weight: card.confidence,
        dashed: false,
        color: cardColors.edge
      });

      // 4. Extracted Evidence Finding Node (Projecting outward from paper)
      if (card.highlightedSentence) {
        const findingId = `node-finding-${card.id}`;
        // Position slightly outward from paper
        const fx = px + (px >= centerX ? 85 : -85);
        const fy = py + (py >= centerY ? 60 : -60);

        const findingNode: GraphNode = {
          id: findingId,
          type: 'finding',
          label: `Finding: "${card.highlightedSentence.slice(0, 32)}..."`,
          sublabel: 'EXTRACTED REASONING EVIDENCE',
          verdict: card.verdictContribution,
          confidence: card.confidence,
          data: {
            parentPaperTitle: card.title,
            sentence: card.highlightedSentence,
            verdict: card.verdictContribution
          },
          x: fx,
          y: fy,
          radius: 20,
          color: '#0f172a',
          borderColor: cardColors.border,
          textColor: '#94a3b8',
          glowColor: cardColors.glow
        };
        nList.push(findingNode);

        // Edge from finding to paper
        eList.push({
          id: `edge-${findingId}-${paperNodeId}`,
          source: findingId,
          target: paperNodeId,
          type: 'EXTRACTS',
          label: 'EVIDENCE EXCERPT',
          dashed: true,
          color: cardColors.border
        });
      }

      // Link paper to first concept
      if (extractedConcepts.length > 0) {
        const conceptTargetId = `node-concept-${idx % extractedConcepts.length}`;
        eList.push({
          id: `edge-${paperNodeId}-${conceptTargetId}`,
          source: paperNodeId,
          target: conceptTargetId,
          type: 'RELATES_TO',
          label: 'DISCUSSES',
          dashed: true,
          color: 'rgba(99, 102, 241, 0.25)'
        });
      }
    });

    // 5. Cross-Paper Consensus & Controversy Links (Paper-to-Paper Corroborations)
    for (let i = 0; i < papers.length; i++) {
      for (let j = i + 1; j < papers.length; j++) {
        const p1 = papers[i];
        const p2 = papers[j];
        const id1 = `node-paper-${p1.id}`;
        const id2 = `node-paper-${p2.id}`;

        if (p1.verdictContribution === p2.verdictContribution && p1.verdictContribution === 'SUPPORT') {
          // Corroboration consensus link
          eList.push({
            id: `edge-corroborate-${p1.id}-${p2.id}`,
            source: id1,
            target: id2,
            type: 'CORROBORATES',
            label: 'CORROBORATES CONSENSUS',
            dashed: true,
            color: '#10b981'
          });
        } else if (
          (p1.verdictContribution === 'SUPPORT' && p2.verdictContribution === 'CONTRADICT') ||
          (p1.verdictContribution === 'CONTRADICT' && p2.verdictContribution === 'SUPPORT')
        ) {
          // Scientific dispute / contest link
          eList.push({
            id: `edge-dispute-${p1.id}-${p2.id}`,
            source: id1,
            target: id2,
            type: 'CONTESTS',
            label: 'CONTESTS / DISPUTES',
            dashed: true,
            color: '#ef4444'
          });
        }
      }
    }

    return { nodes: nList, edges: eList };
  }, [result, extractedConcepts, layoutMode]);

  // Apply custom dragged positions
  const finalNodes = useMemo(() => {
    return nodes.map(n => {
      const custom = nodeCustomPositions[n.id];
      if (custom) {
        return { ...n, x: custom.x, y: custom.y };
      }
      return n;
    });
  }, [nodes, nodeCustomPositions]);

  // Node Map for fast coordinate lookup
  const nodeMap = useMemo(() => {
    const map = new Map<string, GraphNode>();
    finalNodes.forEach(n => map.set(n.id, n));
    return map;
  }, [finalNodes]);

  // Filter nodes & edges according to Stance filter
  const visibleNodes = useMemo(() => {
    if (filterStance === 'ALL') return finalNodes;
    if (filterStance === 'CONSENSUS') {
      // Show papers involved in corroborations or disputes
      return finalNodes.filter(n => n.type === 'claim' || n.type === 'concept' || (n.type === 'paper' && n.verdict === 'SUPPORT'));
    }
    return finalNodes.filter(n => {
      if (n.type === 'claim' || n.type === 'concept') return true;
      return n.verdict === filterStance;
    });
  }, [finalNodes, filterStance]);

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map(n => n.id)), [visibleNodes]);

  const visibleEdges = useMemo(() => {
    return edges.filter(e => {
      if (!visibleNodeIds.has(e.source) || !visibleNodeIds.has(e.target)) return false;
      if (filterStance === 'ALL') return true;
      if (filterStance === 'CONSENSUS') return e.type === 'CORROBORATES' || e.type === 'CONTESTS' || e.type === 'SUPPORTS';
      if (filterStance === 'SUPPORT') return e.type === 'SUPPORTS' || e.type === 'CORROBORATES' || e.type === 'EXTRACTS' || e.type === 'RELATES_TO';
      if (filterStance === 'CONTRADICT') return e.type === 'CONTRADICTS' || e.type === 'CONTESTS' || e.type === 'EXTRACTS' || e.type === 'RELATES_TO';
      return true;
    });
  }, [edges, visibleNodeIds, filterStance]);

  // Node Drag handlers
  const handleNodeMouseDown = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setDraggedNodeId(id);
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    if (draggedNodeId) {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      // Convert screen mouse coords to SVG space
      const svgX = (e.clientX - rect.left - pan.x) / zoom;
      const svgY = (e.clientY - rect.top - pan.y) / zoom;

      setNodeCustomPositions(prev => ({
        ...prev,
        [draggedNodeId]: { x: Math.round(svgX), y: Math.round(svgY) }
      }));
    } else if (isDraggingCanvas) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleCanvasMouseUp = () => {
    setDraggedNodeId(null);
    setIsDraggingCanvas(false);
  };

  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDraggingCanvas(true);
      setDragStart({
        x: e.clientX - pan.x,
        y: e.clientY - pan.y
      });
    }
  };

  const resetGraphView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setNodeCustomPositions({});
    setSelectedNodeId(null);
  };

  // Node inspection details
  const activeSelectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return finalNodes.find(n => n.id === selectedNodeId) || null;
  }, [selectedNodeId, finalNodes]);

  // Connected edges for selected or hovered node
  const activeFocusId = hoveredNodeId || selectedNodeId;
  const connectedNeighbors = useMemo(() => {
    if (!activeFocusId) return new Set<string>();
    const set = new Set<string>();
    set.add(activeFocusId);
    visibleEdges.forEach(e => {
      if (e.source === activeFocusId) set.add(e.target);
      if (e.target === activeFocusId) set.add(e.source);
    });
    return set;
  }, [activeFocusId, visibleEdges]);

  // Calculate consensus metrics
  const stats = useMemo(() => {
    const papers = result.evidence || [];
    const supportCount = papers.filter(p => p.verdictContribution === 'SUPPORT').length;
    const contradictCount = papers.filter(p => p.verdictContribution === 'CONTRADICT').length;
    const neutralCount = papers.filter(p => p.verdictContribution === 'NOT ENOUGH INFO').length;
    const consensusLinks = edges.filter(e => e.type === 'CORROBORATES').length;
    const disputeLinks = edges.filter(e => e.type === 'CONTESTS').length;

    return {
      totalPapers: papers.length,
      supportCount,
      contradictCount,
      neutralCount,
      consensusLinks,
      disputeLinks
    };
  }, [result.evidence, edges]);

  return (
    <div 
      className={`relative rounded-xl border border-slate-200 dark:border-white/10 bg-slate-900/60 backdrop-blur-md overflow-hidden transition-all duration-300 ${
        isFullscreen ? 'fixed inset-4 z-50 shadow-2xl bg-slate-950 flex flex-col' : 'my-8'
      }`}
    >
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-slate-200 dark:border-white/10 bg-slate-950/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Network className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                <span>SECTION_04: EVIDENCE VERIFICATION & CONSENSUS TOPOLOGY GRAPH</span>
                <span className="px-1.5 py-0.5 text-[9px] rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  INTERACTIVE NLI GRAPH
                </span>
              </h3>
            </div>
            <p className="text-[10px] text-slate-400 font-mono mt-0.5">
              Multi-node topology connecting claim assertions, primary trials, extracted sentence premises, and scientific consensus arcs.
            </p>
          </div>
        </div>

        {/* Toolbar Controls */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          {/* Stance Filter */}
          <div className="flex items-center bg-black/40 border border-white/10 rounded-lg p-0.5">
            <button
              onClick={() => setFilterStance('ALL')}
              className={`px-2 py-1 rounded text-[10px] font-semibold transition-all ${
                filterStance === 'ALL' ? 'bg-white/10 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All ({visibleNodes.length})
            </button>
            <button
              onClick={() => setFilterStance('SUPPORT')}
              className={`px-2 py-1 rounded text-[10px] font-semibold transition-all flex items-center gap-1 ${
                filterStance === 'SUPPORT' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'text-emerald-400/70 hover:text-emerald-300'
              }`}
            >
              <CheckCircle2 className="h-2.5 w-2.5" />
              <span>Supports ({stats.supportCount})</span>
            </button>
            <button
              onClick={() => setFilterStance('CONTRADICT')}
              className={`px-2 py-1 rounded text-[10px] font-semibold transition-all flex items-center gap-1 ${
                filterStance === 'CONTRADICT' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'text-rose-400/70 hover:text-rose-300'
              }`}
            >
              <XCircle className="h-2.5 w-2.5" />
              <span>Refutes ({stats.contradictCount})</span>
            </button>
            <button
              onClick={() => setFilterStance('CONSENSUS')}
              className={`px-2 py-1 rounded text-[10px] font-semibold transition-all flex items-center gap-1 ${
                filterStance === 'CONSENSUS' ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40' : 'text-indigo-400/70 hover:text-indigo-300'
              }`}
            >
              <Sparkles className="h-2.5 w-2.5" />
              <span>Consensus Links</span>
            </button>
          </div>

          {/* Layout Mode Selector */}
          <div className="flex items-center bg-black/40 border border-white/10 rounded-lg p-0.5">
            <button
              onClick={() => setLayoutMode('radial')}
              title="Radial Orbit Layout"
              className={`px-2 py-1 rounded text-[10px] ${layoutMode === 'radial' ? 'bg-cobalt/30 text-sky-300 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Radial
            </button>
            <button
              onClick={() => setLayoutMode('bipartite')}
              title="Consensus Wing Bipartite Layout"
              className={`px-2 py-1 rounded text-[10px] ${layoutMode === 'bipartite' ? 'bg-cobalt/30 text-sky-300 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Bipartite
            </button>
            <button
              onClick={() => setLayoutMode('hierarchical')}
              title="Hierarchical Lineage Layout"
              className={`px-2 py-1 rounded text-[10px] ${layoutMode === 'hierarchical' ? 'bg-cobalt/30 text-sky-300 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Hierarchy
            </button>
          </div>

          {/* Zoom & Canvas Actions */}
          <div className="flex items-center gap-1 bg-black/40 border border-white/10 rounded-lg p-0.5">
            <button
              onClick={() => setZoom(z => Math.min(2.5, z + 0.15))}
              className="p-1 hover:bg-white/10 text-slate-300 rounded transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setZoom(z => Math.max(0.5, z - 0.15))}
              className="p-1 hover:bg-white/10 text-slate-300 rounded transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={resetGraphView}
              className="p-1 hover:bg-white/10 text-slate-300 rounded transition-colors"
              title="Reset View"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1 hover:bg-white/10 text-slate-300 rounded transition-colors"
              title={isFullscreen ? "Exit Fullscreen" : "Fullscreen Graph"}
            >
              {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Consensus Metrics Summary Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-5 border-b border-white/5 bg-slate-950/40 text-[10px] font-mono divide-x divide-white/5">
        <div className="px-4 py-2 flex items-center justify-between">
          <span className="text-slate-400">STUDIES CONNECTED</span>
          <span className="font-bold text-slate-200">{stats.totalPapers}</span>
        </div>
        <div className="px-4 py-2 flex items-center justify-between">
          <span className="text-emerald-400">SUPPORT RATIO</span>
          <span className="font-bold text-emerald-400">{stats.supportCount} / {stats.totalPapers}</span>
        </div>
        <div className="px-4 py-2 flex items-center justify-between">
          <span className="text-rose-400">REFUTED RATIO</span>
          <span className="font-bold text-rose-400">{stats.contradictCount} / {stats.totalPapers}</span>
        </div>
        <div className="px-4 py-2 flex items-center justify-between">
          <span className="text-indigo-400">CROSS-STUDY CORROBORATION</span>
          <span className="font-bold text-indigo-400">{stats.consensusLinks} ARCS</span>
        </div>
        <div className="px-4 py-2 flex items-center justify-between col-span-2 sm:col-span-1">
          <span className="text-amber-400">ACTIVE CONTROVERSY</span>
          <span className="font-bold text-amber-400">{stats.disputeLinks > 0 ? `${stats.disputeLinks} DISPUTES` : 'SETTLED CONSENSUS'}</span>
        </div>
      </div>

      {/* Main Canvas & Inspection Sidebar Layout */}
      <div className="relative flex-1 flex flex-col lg:flex-row overflow-hidden" style={{ minHeight: isFullscreen ? 'calc(100vh - 120px)' : '550px' }}>
        
        {/* Graph SVG Interactive Canvas */}
        <div
          ref={containerRef}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          className={`relative flex-1 bg-[#050b14] overflow-hidden select-none cursor-grab active:cursor-grabbing ${
            isDraggingCanvas ? 'cursor-grabbing' : ''
          }`}
        >
          {/* Subtle Grid Backdrop */}
          <div 
            className="absolute inset-0 pointer-events-none opacity-25"
            style={{
              backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.15) 1px, transparent 0)',
              backgroundSize: '24px 24px',
              transform: `translate(${pan.x % 24}px, ${pan.y % 24}px)`
            }}
          />

          {/* Interactive SVG */}
          <svg 
            className="w-full h-full"
            style={{ minHeight: isFullscreen ? 'calc(100vh - 120px)' : '550px' }}
          >
            <defs>
              {/* Arrow Markers for Directed Verification Edges */}
              <marker id="arrow-supports" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981" />
              </marker>
              <marker id="arrow-contradicts" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" />
              </marker>
              <marker id="arrow-insufficient" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#f59e0b" />
              </marker>
              <marker id="arrow-concept" viewBox="0 0 10 10" refX="20" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#818cf8" />
              </marker>

              {/* Glowing Filters */}
              <filter id="glow-emerald" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
              <filter id="glow-rose" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
              <filter id="glow-indigo" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Transform Group for Pan & Zoom */}
            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              
              {/* Render Connecting Edges */}
              {visibleEdges.map((edge) => {
                const sourceNode = nodeMap.get(edge.source);
                const targetNode = nodeMap.get(edge.target);
                if (!sourceNode || !targetNode) return null;

                const isConnectedToFocus = activeFocusId ? (edge.source === activeFocusId || edge.target === activeFocusId) : true;
                const edgeOpacity = activeFocusId ? (isConnectedToFocus ? 1 : 0.15) : 0.75;

                // Curved path for corroboration / dispute cross-links between papers
                const isCrossLink = edge.type === 'CORROBORATES' || edge.type === 'CONTESTS';
                let pathD = '';

                if (isCrossLink) {
                  // Arc curve between peer papers
                  const dx = targetNode.x - sourceNode.x;
                  const dy = targetNode.y - sourceNode.y;
                  const dr = Math.sqrt(dx * dx + dy * dy) * 1.25;
                  pathD = `M ${sourceNode.x} ${sourceNode.y} A ${dr} ${dr} 0 0,1 ${targetNode.x} ${targetNode.y}`;
                } else {
                  pathD = `M ${sourceNode.x} ${sourceNode.y} L ${targetNode.x} ${targetNode.y}`;
                }

                const markerEnd = 
                  edge.type === 'SUPPORTS' ? 'url(#arrow-supports)' :
                  edge.type === 'CONTRADICTS' ? 'url(#arrow-contradicts)' :
                  edge.type === 'INSUFFICIENT' ? 'url(#arrow-insufficient)' :
                  edge.type === 'RELATES_TO' ? 'url(#arrow-concept)' : undefined;

                return (
                  <g key={edge.id} className="transition-opacity duration-300" opacity={edgeOpacity}>
                    {/* Underlying thicker line for hover detection */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke={edge.color}
                      strokeWidth={edge.weight ? Math.max(2, (edge.weight / 100) * 4) : (isCrossLink ? 2.5 : 1.5)}
                      strokeDasharray={edge.dashed ? (isCrossLink ? '5,5' : '3,3') : undefined}
                      markerEnd={markerEnd}
                      className={isCrossLink ? 'animate-pulse' : ''}
                    />

                    {/* Edge Label (only shown if connected to focus or hovered) */}
                    {(isConnectedToFocus || isCrossLink) && (
                      <text
                        x={(sourceNode.x + targetNode.x) / 2}
                        y={(sourceNode.y + targetNode.y) / 2 - (isCrossLink ? 12 : 6)}
                        fill={edge.color}
                        fontSize="9"
                        fontFamily="monospace"
                        fontWeight="bold"
                        textAnchor="middle"
                        className="bg-black/80 px-1 select-none pointer-events-none"
                      >
                        {edge.label}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Render Nodes */}
              {visibleNodes.map((node) => {
                const isFocused = activeFocusId ? connectedNeighbors.has(node.id) : true;
                const isSelected = selectedNodeId === node.id;
                const isHovered = hoveredNodeId === node.id;
                const nodeOpacity = activeFocusId ? (isFocused ? 1 : 0.2) : 1;

                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    opacity={nodeOpacity}
                    className="cursor-pointer transition-opacity duration-300"
                    onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedNodeId(node.id === selectedNodeId ? null : node.id);
                    }}
                    onMouseEnter={() => setHoveredNodeId(node.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                  >
                    {/* Atmospheric Glow Ring */}
                    <circle
                      r={node.radius + (isSelected ? 10 : isHovered ? 6 : 2)}
                      fill={node.glowColor}
                      opacity={isSelected || isHovered ? 0.7 : 0.25}
                      className="transition-all duration-300"
                    />

                    {/* Central Node Circle */}
                    <circle
                      r={node.radius}
                      fill={node.color}
                      stroke={node.borderColor}
                      strokeWidth={isSelected ? 3.5 : isHovered ? 2.5 : 1.5}
                      className="transition-all duration-200"
                    />

                    {/* Custom Inner Graphic per node type */}
                    {node.type === 'claim' ? (
                      <g>
                        <circle r={node.radius - 8} fill="none" stroke={node.borderColor} strokeDasharray="3,3" opacity="0.6" />
                        <text
                          y="-10"
                          textAnchor="middle"
                          fill="#ffffff"
                          fontSize="9"
                          fontFamily="monospace"
                          fontWeight="bold"
                          className="pointer-events-none select-none tracking-wider"
                        >
                          [CLAIM_HUB]
                        </text>
                        <text
                          y="6"
                          textAnchor="middle"
                          fill={node.textColor}
                          fontSize="10"
                          fontFamily="monospace"
                          fontWeight="extrabold"
                          className="pointer-events-none select-none"
                        >
                          {node.verdict === 'SUPPORT' ? 'SUPPORTED' : node.verdict === 'CONTRADICT' ? 'CONTRADICTED' : 'NOT ENOUGH INFO'}
                        </text>
                        <text
                          y="20"
                          textAnchor="middle"
                          fill="#94a3b8"
                          fontSize="8"
                          fontFamily="monospace"
                          className="pointer-events-none select-none"
                        >
                          {node.confidence}% CONFIDENCE
                        </text>
                      </g>
                    ) : node.type === 'paper' ? (
                      <g>
                        <text
                          y="-6"
                          textAnchor="middle"
                          fill={node.textColor}
                          fontSize="9"
                          fontFamily="monospace"
                          fontWeight="bold"
                          className="pointer-events-none select-none"
                        >
                          {node.data?.journal ? node.data.journal.slice(0, 10).toUpperCase() : 'PAPER'}
                        </text>
                        <text
                          y="8"
                          textAnchor="middle"
                          fill="#ffffff"
                          fontSize="8.5"
                          fontFamily="monospace"
                          fontWeight="bold"
                          className="pointer-events-none select-none"
                        >
                          {node.data?.year || '2021'}
                        </text>
                        <text
                          y="18"
                          textAnchor="middle"
                          fill={node.verdict === 'SUPPORT' ? '#34d399' : node.verdict === 'CONTRADICT' ? '#f87171' : '#fbbf24'}
                          fontSize="7"
                          fontFamily="monospace"
                          fontWeight="extrabold"
                          className="pointer-events-none select-none"
                        >
                          [{node.confidence}%]
                        </text>
                      </g>
                    ) : node.type === 'concept' ? (
                      <g>
                        <text
                          y="3"
                          textAnchor="middle"
                          fill="#c7d2fe"
                          fontSize="8"
                          fontFamily="monospace"
                          fontWeight="bold"
                          className="pointer-events-none select-none"
                        >
                          {node.label.slice(0, 9)}
                        </text>
                      </g>
                    ) : (
                      <g>
                        <text
                          y="3"
                          textAnchor="middle"
                          fill="#cbd5e1"
                          fontSize="7.5"
                          fontFamily="monospace"
                          className="pointer-events-none select-none"
                        >
                          QUOTE
                        </text>
                      </g>
                    )}

                    {/* Node Label Pill Below */}
                    <g transform={`translate(0, ${node.radius + 14})`}>
                      <rect
                        x="-75"
                        y="-10"
                        width="150"
                        height="20"
                        rx="4"
                        fill="rgba(3, 7, 18, 0.85)"
                        stroke={isHovered || isSelected ? node.borderColor : 'rgba(255, 255, 255, 0.1)'}
                        strokeWidth="1"
                      />
                      <text
                        x="0"
                        y="3"
                        textAnchor="middle"
                        fill={isHovered || isSelected ? '#ffffff' : '#94a3b8'}
                        fontSize="8.5"
                        fontFamily="sans-serif"
                        fontWeight={node.type === 'claim' ? 'bold' : 'normal'}
                        className="pointer-events-none select-none"
                      >
                        {node.label.length > 24 ? node.label.slice(0, 22) + '...' : node.label}
                      </text>
                    </g>
                  </g>
                );
              })}
            </g>
          </svg>

          {/* Quick Graph Navigation Overlay Instructions */}
          <div className="absolute bottom-3 left-3 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 text-[9px] font-mono text-slate-400 flex items-center gap-3 pointer-events-none">
            <span>🖱️ DRAG NODE: REPOSITION</span>
            <span>•</span>
            <span>SCROLL: ZOOM CANVAS</span>
            <span>•</span>
            <span>CLICK: INSPECT DETAILS</span>
          </div>

          {/* Legend Overlay */}
          <div className="absolute top-3 right-3 bg-black/75 backdrop-blur-md p-3 rounded-xl border border-white/10 text-[10px] font-mono space-y-1.5 pointer-events-none max-w-[200px]">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block border-b border-white/10 pb-1 mb-1">
              TOPOLOGY ENCODING
            </span>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              <span className="text-emerald-300">Supporting Study / Edge</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-rose-400" />
              <span className="text-rose-300">Refuting / Dispute Edge</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-indigo-400" />
              <span className="text-indigo-300">Biomedical Entity Hub</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              <span className="text-amber-300">Extracted Quote Premise</span>
            </div>
            <div className="flex items-center gap-2 pt-1 border-t border-white/5 text-[9px] text-slate-400">
              <span className="h-1.5 w-3 border-b-2 border-dashed border-emerald-400" />
              <span>Cross-Paper Corroboration</span>
            </div>
          </div>
        </div>

        {/* Node Inspection Drawer (Slides in on right or below) */}
        <AnimatePresence>
          {activeSelectedNode && (
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 50 }}
              transition={{ duration: 0.25 }}
              className="w-full lg:w-96 border-t lg:border-t-0 lg:border-l border-white/10 bg-slate-950/95 backdrop-blur-xl p-5 overflow-y-auto space-y-4 text-xs font-mono"
              style={{ maxHeight: isFullscreen ? 'calc(100vh - 120px)' : '550px' }}
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div className="flex items-center gap-2">
                  <div 
                    className="h-3 w-3 rounded-full" 
                    style={{ backgroundColor: activeSelectedNode.borderColor }} 
                  />
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    NODE_INSPECTOR: {activeSelectedNode.type.toUpperCase()}
                  </span>
                </div>
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="text-slate-400 hover:text-white text-[10px] px-1.5 py-0.5 rounded border border-white/10"
                >
                  CLOSE [X]
                </button>
              </div>

              {/* Title & Stance */}
              <div>
                <span className="text-[9px] uppercase tracking-wider text-slate-500 block mb-1">
                  IDENTIFIER / LABEL
                </span>
                <h4 className="font-serif text-sm font-semibold text-slate-100 leading-snug">
                  {activeSelectedNode.data?.title || activeSelectedNode.label}
                </h4>
                {activeSelectedNode.verdict && (
                  <div className="mt-2 flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                      activeSelectedNode.verdict === 'SUPPORT' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' :
                      activeSelectedNode.verdict === 'CONTRADICT' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' :
                      'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    }`}>
                      {activeSelectedNode.verdict}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      NLI Confidence: <strong>{activeSelectedNode.confidence}%</strong>
                    </span>
                  </div>
                )}
              </div>

              {/* Meta details if Paper */}
              {activeSelectedNode.type === 'paper' && activeSelectedNode.data && (
                <div className="space-y-3 pt-2 border-t border-white/5">
                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-slate-500 block">JOURNAL & CITATION</span>
                    <p className="text-slate-300 text-xs mt-0.5">
                      {activeSelectedNode.data.journal} ({activeSelectedNode.data.year})
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      Authors: {activeSelectedNode.data.authors}
                    </p>
                  </div>

                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-slate-500 block mb-1">EXTRACTED GROUNDING SENTENCE</span>
                    <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-[11px] text-emerald-200 leading-relaxed font-sans">
                      "{activeSelectedNode.data.highlightedSentence}"
                    </div>
                  </div>

                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-slate-500 block mb-1">TRIAL ABSTRACT</span>
                    <p className="text-[11px] text-slate-400 font-sans leading-relaxed max-h-36 overflow-y-auto pr-1">
                      {activeSelectedNode.data.abstract}
                    </p>
                  </div>

                  {activeSelectedNode.data.link && (
                    <div className="pt-2 border-t border-white/10">
                      <a
                        href={activeSelectedNode.data.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-cobalt hover:underline text-xs font-bold"
                      >
                        <span>[VIEW DOI / NCBI PUBMED RECORD]</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  )}
                </div>
              )}

              {/* Meta details if Finding */}
              {activeSelectedNode.type === 'finding' && activeSelectedNode.data && (
                <div className="space-y-3 pt-2 border-t border-white/5">
                  <span className="text-[9px] uppercase tracking-wider text-slate-500 block">EXCERPT PREMISE</span>
                  <div className="p-3 rounded-lg bg-slate-900 border border-white/10 text-xs text-slate-200 font-sans leading-relaxed">
                    "{activeSelectedNode.data.sentence}"
                  </div>
                  <span className="text-[10px] text-slate-400 block">
                    Source: {activeSelectedNode.data.parentPaperTitle}
                  </span>
                </div>
              )}

              {/* Meta details if Concept */}
              {activeSelectedNode.type === 'concept' && activeSelectedNode.data && (
                <div className="space-y-3 pt-2 border-t border-white/5">
                  <span className="text-[9px] uppercase tracking-wider text-slate-500 block">BIOMEDICAL DOMAIN ENTITY</span>
                  <p className="text-xs text-slate-300 font-sans leading-relaxed">
                    {activeSelectedNode.data.description}
                  </p>
                  <div className="p-2.5 rounded bg-indigo-500/10 border border-indigo-500/30 text-[10px] text-indigo-300">
                    Connects empirical assertions with indexed trial findings.
                  </div>
                </div>
              )}

              {/* Connected Relationships in Graph */}
              <div className="pt-3 border-t border-white/10 space-y-2">
                <span className="text-[9px] uppercase tracking-wider text-slate-500 block font-bold">
                  DIRECT TOPOLOGICAL ARCS ({Array.from(connectedNeighbors).length - 1})
                </span>
                <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                  {visibleEdges
                    .filter(e => e.source === activeSelectedNode.id || e.target === activeSelectedNode.id)
                    .map(e => {
                      const otherId = e.source === activeSelectedNode.id ? e.target : e.source;
                      const otherNode = nodeMap.get(otherId);
                      if (!otherNode) return null;

                      return (
                        <div 
                          key={e.id}
                          onClick={() => setSelectedNodeId(otherId)}
                          className="p-1.5 rounded bg-white/5 hover:bg-white/10 transition-colors cursor-pointer flex items-center justify-between text-[10px]"
                        >
                          <span className="text-slate-300 truncate max-w-[170px]">{otherNode.label}</span>
                          <span className="font-bold text-[8.5px] px-1 rounded" style={{ color: e.color }}>
                            {e.label}
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
};
