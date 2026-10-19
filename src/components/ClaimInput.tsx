import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { Search, FlaskConical, CornerDownLeft, X, ShieldAlert, BarChart2, Mic, MicOff, Volume2 } from 'lucide-react';

interface ClaimInputProps {
  onVerify: (claim: string) => void;
  onFocusChange?: (focused: boolean) => void;
  currentUser?: { name: string; email: string; institution: string } | null;
}

export const ClaimInput: React.FC<ClaimInputProps> = ({ onVerify, onFocusChange, currentUser }) => {
  const [claim, setClaim] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [audioFeedback, setAudioFeedback] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const shouldReduceMotion = useReducedMotion();

  const placeholders = [
    "Vitamin D prevents influenza...",
    "Coffee increases lifespan...",
    "5G causes cancer...",
    "Artificial sweeteners cause diabetes...",
    "Climate change is reversible..."
  ];

  const examples = [
    {
      id: "CAL-01",
      text: "Vitamin D supplementation reduces the risk of acute respiratory infections.",
      verdict: "SUPPORTED",
      badgeColor: "border-emerald-500/30 text-emerald-400 bg-emerald-500/5"
    },
    {
      id: "CAL-02",
      text: "Smoking cessation has no effect on lung cancer risk reduction.",
      verdict: "CONTRADICTED",
      badgeColor: "border-rose-500/30 text-rose-400 bg-rose-500/5"
    },
    {
      id: "CAL-03",
      text: "Aspirin reduces the risk of colorectal cancer in all populations.",
      verdict: "NOT ENOUGH EVIDENCE",
      badgeColor: "border-amber-500/30 text-amber-400 bg-amber-500/5"
    }
  ];

  // Rotate placeholders every 4 seconds
  useEffect(() => {
    if (claim !== '' || isFocused) return;
    const interval = setInterval(() => {
      setPlaceholderIdx(prev => (prev + 1) % placeholders.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [claim, isFocused]);

  const triggerVerification = () => {
    if (claim.trim().length >= 10 && !isAnalyzing) {
      setIsAnalyzing(true);
      // Brief aesthetic delay to allow the "Analyzing..." button sweep to render
      setTimeout(() => {
        onVerify(claim.trim());
      }, 1000);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    triggerVerification();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      triggerVerification();
    }
  };

  const toggleAudioRecording = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setAudioFeedback("Speech recognition not supported in this browser. Please use Google Chrome or Edge.");
      setTimeout(() => setAudioFeedback(null), 4000);
      return;
    }

    if (isRecording) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
      setAudioFeedback("Grok Audio processing captured claim...");
      setTimeout(() => setAudioFeedback(null), 3000);
    } else {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
          setIsRecording(true);
          setAudioFeedback("Listening... Speak your scientific assertion clearly.");
        };

        recognition.onresult = (event: any) => {
          const transcript = Array.from(event.results)
            .map((result: any) => result[0].transcript)
            .join('');
          setClaim(transcript);
        };

        recognition.onerror = (event: any) => {
          console.error('Speech recognition error:', event.error);
          setIsRecording(false);
          setAudioFeedback(`Audio capture notice: ${event.error}`);
          setTimeout(() => setAudioFeedback(null), 3500);
        };

        recognition.onend = () => {
          setIsRecording(false);
          setAudioFeedback("Groq Audio (Whisper-v3): Spoken claim captured successfully.");
          setTimeout(() => setAudioFeedback(null), 3000);
        };

        recognitionRef.current = recognition;
        recognition.start();
      } catch (err) {
        console.error('Error starting speech recognition:', err);
        setIsRecording(false);
      }
    }
  };

  const countStr = claim.trim().length.toString().padStart(3, '0');

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      
      {/* Instrumentation Console Header */}
      <div className="instrument-card p-6 mb-8 border-slate-200 dark:border-white/5 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full filter blur-3xl pointer-events-none" />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-white/5 pb-4 mb-4">
          <div>
            <h2 className="font-serif text-2xl font-semibold tracking-tight text-ink">
              {currentUser ? `Dr. ${currentUser.name}'s Workspace` : 'SciVerify Analysis Console'}
            </h2>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest mt-1">
              Natural Language Processing Evidence Retrieval & Verification
            </p>
          </div>
          <div className="flex items-center gap-4 text-[10px] font-mono text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 bg-emerald-500 rounded-full animate-pulse" />
              STATUS: ONLINE
            </span>
            <span className="border-l border-slate-200 dark:border-white/10 pl-4">MODEL: DeBERTa_v3_NLI</span>
          </div>
        </div>
        <p className="text-xs leading-relaxed text-slate-400 font-sans max-w-2xl">
          This laboratory terminal processes plain-language biomedical assertions, retrieves peer-reviewed research papers using semantic vector search, and evaluates claim alignment. Enter an assertion below to initiate inference.
        </p>
      </div>

      {/* Main Verification Instrument */}
      <form onSubmit={handleSubmit} className="relative">
        <motion.div 
          className={`instrument-card p-6 border transition-all duration-300 relative ${
            isFocused ? 'border-cobalt/50 bg-console/80' : 'border-slate-200 dark:border-white/5 bg-console/40'
          }`}
          onHoverStart={() => setIsHovered(true)}
          onHoverEnd={() => setIsHovered(false)}
          animate={isFocused ? { 
            boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.5), 0 0 25px rgba(59, 130, 246, 0.08)"
          } : isHovered ? {
            boxShadow: "0 15px 30px -15px rgba(0, 0, 0, 0.4), 0 0 15px rgba(255, 255, 255, 0.02)"
          } : {
            boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.37)"
          }}
          transition={{ duration: 0.3 }}
        >
          {/* Subtle Technical Calibration Markers */}
          <div className="absolute top-2 left-3 flex gap-2 text-[8px] font-mono text-slate-600 select-none">
            <span>[VOLT_IN_CAL_1.02]</span>
            <span>[SYS_SENS_ACTIVE]</span>
          </div>

          {/* Absolute Cursor-Follower Glow */}
          {isFocused && (
            <div className="absolute top-0 right-0 w-24 h-24 bg-cobalt/10 rounded-full filter blur-2xl pointer-events-none select-none" />
          )}
          
          {/* Clear Button */}
          {claim && !isAnalyzing && (
            <button
              type="button"
              onClick={() => setClaim('')}
              className="absolute top-2 right-3 p-1 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer focus:outline-none"
              title="Clear entry"
            >
              <X className="h-4 w-4" />
            </button>
          )}

          {/* Audio Feedback Notification */}
          <AnimatePresence>
            {audioFeedback && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                className="mb-3 px-3 py-1.5 rounded-lg bg-cobalt/10 border border-cobalt/20 text-cobalt flex items-center gap-2 text-xs font-mono"
              >
                <Volume2 className="h-3.5 w-3.5 animate-pulse" />
                <span>{audioFeedback}</span>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="mt-2 flex gap-4 items-start relative min-h-[90px]">
            {/* Flask icon - slowly breathes */}
            <motion.div 
              className="mt-1.5 text-slate-500 shrink-0"
              animate={!shouldReduceMotion ? {
                opacity: [0.5, 0.8, 0.5],
                scale: [0.97, 1.03, 0.97]
              } : {}}
              transition={{ repeat: Infinity, duration: 3.5, ease: "easeInOut" }}
            >
              <FlaskConical className={`h-5 w-5 transition-colors duration-300 ${isFocused ? 'text-cobalt' : 'text-slate-500'}`} />
            </motion.div>
            
            <div className="flex-1 relative">
              {/* Animated Placeholder Layer */}
              {claim === '' && !isFocused && (
                <AnimatePresence mode="wait">
                  <motion.div
                    key={placeholderIdx}
                    initial={{ y: 6, opacity: 0 }}
                    animate={{ y: 0, opacity: 0.3 }}
                    exit={{ y: -6, opacity: 0 }}
                    transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                    className="absolute pointer-events-none select-none text-slate-400 font-serif text-sm italic"
                    style={{ top: '6px' }}
                  >
                    {placeholders[placeholderIdx]}
                  </motion.div>
                </AnimatePresence>
              )}

              <textarea
                value={claim}
                onChange={(e) => setClaim(e.target.value)}
                onFocus={() => {
                  setIsFocused(true);
                  if (onFocusChange) onFocusChange(true);
                }}
                onBlur={() => {
                  setIsFocused(false);
                  if (onFocusChange) onFocusChange(false);
                }}
                onKeyDown={handleKeyDown}
                rows={3}
                disabled={isAnalyzing}
                className="w-full resize-none border-0 bg-transparent py-1.5 text-sm font-serif text-ink placeholder-transparent focus:ring-0 focus:outline-none min-h-[80px]"
                maxLength={280}
              />
            </div>
          </div>

          {/* Metric Status bar */}
          <div className="mt-4 flex items-center justify-between border-t border-slate-200 dark:border-white/5 pt-4">
            
            {/* Ticking monospace layout length counter */}
            <div className="font-mono text-[10px] text-slate-500 select-none flex items-center">
              <span>LENGTH:&nbsp;</span>
              <span className="inline-flex overflow-hidden h-3.5 text-slate-400 font-bold">
                {countStr.split('').map((char, index) => (
                  <motion.span
                    key={`${index}-${char}`}
                    initial={shouldReduceMotion ? {} : { y: -10, opacity: 0 }}
                    animate={shouldReduceMotion ? {} : { y: 0, opacity: 1 }}
                    transition={{ duration: 0.16, ease: "easeOut" }}
                    className="inline-block"
                  >
                    {char}
                  </motion.span>
                ))}
              </span>
              <span>/280 B</span>
              {claim.trim().length > 0 && claim.trim().length < 10 && (
                <span className="text-rose-400 font-medium ml-3 flex items-center gap-1.5 success-glow">
                  <ShieldAlert className="h-3 w-3" /> Min 10 bytes required
                </span>
              )}
            </div>
            
            {/* Actions: Grok Audio Input + Verify Button */}
            <div className="flex items-center gap-3">
              {/* Grok Audio Record Button */}
              <button
                type="button"
                onClick={toggleAudioRecording}
                className={`flex items-center gap-2 px-3.5 py-2 font-mono text-[11px] uppercase tracking-wider rounded-lg border transition-all cursor-pointer select-none focus:outline-none ${
                  isRecording
                    ? 'bg-rose-500 text-white border-rose-600 animate-pulse shadow-lg shadow-rose-500/20'
                    : 'bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-white/10'
                }`}
                title="Speak a scientific claim via Groq Whisper-v3 Speech Model"
              >
                {isRecording ? (
                  <>
                    <MicOff className="h-3.5 w-3.5 text-white animate-spin" />
                    <span className="font-bold">Recording...</span>
                  </>
                ) : (
                  <>
                    <Mic className="h-3.5 w-3.5 text-cobalt" />
                    <span>Groq Voice</span>
                  </>
                )}
              </button>

              {/* Expensive Verify Button */}
              <motion.button
                type="submit"
                disabled={claim.trim().length < 10 || isAnalyzing}
                whileTap={claim.trim().length >= 10 && !isAnalyzing && !shouldReduceMotion ? { scale: 0.96 } : {}}
                className={`relative overflow-hidden flex items-center gap-2.5 px-6 py-2.5 font-mono text-xs uppercase tracking-widest border transition-all duration-300 cursor-pointer select-none focus:outline-none rounded-lg ${
                  claim.trim().length >= 10 && !isAnalyzing
                    ? 'bg-cobalt text-white border-cobalt/60 hover:bg-cobalt/90 shadow-lg shadow-cobalt/10'
                    : isAnalyzing
                    ? 'bg-slate-100 text-slate-400 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-white/10 cursor-not-allowed shadow-none'
                    : 'bg-slate-50 text-slate-400 border-slate-200 dark:bg-white/5 dark:text-slate-500 dark:border-white/5 cursor-not-allowed shadow-none'
                }`}
              >
              {/* Shimmer light sweep */}
              {claim.trim().length >= 10 && !isAnalyzing && !shouldReduceMotion && (
                <motion.span
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/15 to-transparent -skew-x-12 block pointer-events-none"
                  initial={{ left: '-100%' }}
                  animate={{ left: '100%' }}
                  transition={{ duration: 1.8, repeat: Infinity, repeatDelay: 3, ease: "easeInOut" }}
                />
              )}
              
              <Search className={`h-3.5 w-3.5 relative z-10 transition-transform ${isAnalyzing ? 'animate-spin' : ''}`} />
              <span className="relative z-10 font-bold">
                {isAnalyzing ? 'Analyzing...' : 'Verify Assertion'}
              </span>
              {!isAnalyzing && (
                <span className="relative z-10 border-l border-slate-300 dark:border-white/20 pl-2 text-[9px] text-slate-500 dark:text-white/50 font-normal">
                  <CornerDownLeft className="inline h-2.5 w-2.5 -mt-0.5" /> Ent
                </span>
              )}
            </motion.button>
          </div>
        </div>
      </motion.div>
    </form>

      {/* Structured Calibration registry table */}
      <div className="mt-12">
        <div className="flex items-center gap-2 border-b border-slate-200 dark:border-white/5 pb-2 mb-4">
          <BarChart2 className="h-4 w-4 text-slate-500" />
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500">
            Calibration Claims Registry
          </h3>
        </div>

        <div className="overflow-hidden border border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-console/20 backdrop-blur-md rounded-xl shadow-md">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-white/5 font-mono text-[11px]">
            <thead className="bg-slate-100 dark:bg-white/5">
              <tr>
                <th scope="col" className="py-3.5 pl-4 pr-3 text-left font-bold text-slate-400 uppercase tracking-wider w-24">ID</th>
                <th scope="col" className="py-3.5 px-3 text-left font-bold text-slate-400 uppercase tracking-wider">Clinical Hypothesis</th>
                <th scope="col" className="py-3.5 px-3 text-left font-bold text-slate-400 uppercase tracking-wider w-40">Logical Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-white/5 bg-transparent">
              {examples.map((example) => (
                <tr 
                  key={example.id}
                  onClick={() => {
                    if (!isAnalyzing) setClaim(example.text);
                  }}
                  className="hover:bg-slate-100 dark:hover:bg-white/5 transition-colors cursor-pointer group"
                >
                  <td className="whitespace-nowrap py-4 pl-4 pr-3 text-slate-500 font-bold group-hover:text-cobalt transition-colors">
                    [{example.id}]
                  </td>
                  <td className="px-3 py-4 font-serif text-slate-600 dark:text-slate-300 group-hover:text-slate-950 dark:group-hover:text-white transition-colors leading-relaxed">
                    "{example.text}"
                  </td>
                  <td className="whitespace-nowrap px-3 py-4">
                    <span className={`inline-flex items-center border px-2 py-0.5 rounded text-[8px] font-bold tracking-wider ${example.badgeColor}`}>
                      {example.verdict}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
