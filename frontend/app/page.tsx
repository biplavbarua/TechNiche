
"use client";

import { useState, useRef } from "react";
import { analyzeIdea, AnalysisResult } from "../lib/api";
import ReactMarkdown from 'react-markdown';
import { Typewriter } from "@/components/typewriter";
import { ArrowRight, Scale, AlertTriangle, Search, Github, Linkedin, Download, FileText } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ThemeToggle } from "@/components/theme-toggle";
import { LearningModal } from "@/components/learning-modal";
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import { Background3D } from "@/components/background-3d";

export default function Home() {
  const [idea, setIdea] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLearningModalOpen, setIsLearningModalOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleAnalyze = async () => {
    if (!idea.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyzeIdea(idea);
      setResult(data);
    } catch (err: any) {
      if (err.message && err.message.includes("fetch")) {
        setError("Failed to connect to the Server. Please checking your internet connection or try again later. If you are the developer, ensure the Backend URL is set correctly.");
      } else {
        setError(err.message || "Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!containerRef.current) return;

    try {
      const canvas = await html2canvas(containerRef.current, {
        scale: 2,
        backgroundColor: "#ffffff" // Force white background for PDF
      });
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
      pdf.save(`Legal_Analysis_${new Date().toISOString().slice(0, 10)}.pdf`);
    } catch (err) {
      console.error("PDF Export failed", err);
    }
  };

  return (
    <div className="min-h-screen text-slate-900 dark:text-slate-200 transition-colors duration-300 font-sans relative overflow-hidden">
      <Background3D />
      <LearningModal isOpen={isLearningModalOpen} onClose={() => setIsLearningModalOpen(false)} />

      <header className="fixed top-0 w-full z-50 border-b border-indigo-500/10 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="w-6 h-6 text-indigo-600 dark:text-indigo-500" />
            <span className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
              LegalAI
            </span>
          </div>
          <nav className="flex items-center gap-4 text-sm font-medium text-slate-600 dark:text-slate-400">
            <a
              href="https://github.com/biplavbarua/TechNiche"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
              title="View Source on GitHub"
            >
              <Github className="w-5 h-5" />
            </a>
            <a
              href="https://www.linkedin.com/in/biplavbarua/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
              title="Connect on LinkedIn"
            >
              <Linkedin className="w-5 h-5" />
            </a>
            <div className="h-4 w-[1px] bg-slate-200 dark:bg-slate-800 mx-1" />
            <button
              onClick={() => setIsLearningModalOpen(true)}
              className="hidden md:flex items-center gap-2 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
            >
              Teach AI
            </button>
            <ThemeToggle />
          </nav>
        </div>
      </header>

      <main className="pt-32 pb-20 px-6 max-w-5xl mx-auto z-10 relative">
        <div className="text-center mb-16 space-y-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-50/50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-300 text-xs font-medium mb-4"
          >
            <span className="w-2 h-2 rounded-full bg-indigo-500 dark:bg-indigo-400 mr-2 animate-pulse"></span>
            Beta Release v1.1
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-5xl md:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white mb-6"
          >
            Navigate Copyright <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-600">
              Without the Lawsuit
            </span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto"
          >
            Describe your creative idea. Our AI analyzes Indian Judiciary cases to identify risks and suggest safe loopholes.
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-white/70 dark:bg-slate-900/70 border border-slate-200 dark:border-indigo-500/20 rounded-2xl p-2 shadow-xl dark:shadow-2xl backdrop-blur-md transition-colors duration-300"
        >
          <div className="relative">
            <textarea
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              placeholder="E.g., I want to make a dark comedy parody of a popular superhero movie..."
              className="w-full h-40 bg-slate-50/50 dark:bg-slate-950/50 rounded-xl p-6 text-lg text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-none transition-all"
            />
            <div className="absolute bottom-4 right-4">
              <button
                onClick={handleAnalyze}
                disabled={loading || !idea.trim()}
                className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 dark:hover:bg-indigo-500 text-white rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/20 active:scale-95"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Analyzing...
                  </span>
                ) : (
                  <>
                    Analyze Risks <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </motion.div>

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-6 p-4 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-700 dark:text-red-200 flex items-center gap-3 backdrop-blur-md"
            >
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              {error}
            </motion.div>
          )}

          {result && (
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-8"
              ref={containerRef}
            >
              {/* Risk Analysis Column */}
              <div className="md:col-span-2 space-y-6">
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-sm p-10 shadow-sm transition-colors duration-300 min-h-[600px] relative">
                  {/* Decorative Header (Paper Like) */}
                  <div className="border-b-2 border-slate-100 dark:border-slate-800 pb-4 mb-8 flex justify-between items-end">
                    <div>
                      <h2 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
                        Legal Analysis
                      </h2>
                      <p className="text-xs text-slate-400 font-mono mt-1">REF: {new Date().toISOString().split('T')[0]}-{Math.floor(Math.random() * 1000)}</p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={handleDownloadPDF}
                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-indigo-600"
                        title="Export to PDF"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                      <Search className="w-6 h-6 text-slate-300 dark:text-slate-600" />
                    </div>
                  </div>

                  <div className="prose prose-slate dark:prose-invert max-w-none text-slate-700 dark:text-slate-300">
                    {/* Render with Typewriter Effect */}
                    <Typewriter text={result.analysis} speed={3}>
                      {(displayText) => (
                        <ReactMarkdown
                          components={{
                            h1: ({ node, ...props }) => <h1 className="text-2xl font-bold mt-8 mb-4 border-l-4 border-indigo-500 pl-4 text-slate-900 dark:text-white" {...props} />,
                            h2: ({ node, ...props }) => <h2 className="text-xl font-bold mt-6 mb-3 text-slate-800 dark:text-slate-100" {...props} />,
                            h3: ({ node, ...props }) => <h3 className="text-lg font-semibold mt-4 mb-2 text-indigo-600 dark:text-indigo-400" {...props} />,
                            ul: ({ node, ...props }) => <ul className="list-disc pl-5 space-y-2 mb-6 text-slate-700 dark:text-slate-300" {...props} />,
                            li: ({ node, ...props }) => <li className="pl-1" {...props} />,
                            p: ({ node, ...props }) => <p className="mb-6 text-lg leading-loose" {...props} />,
                            strong: ({ node, ...props }) => <strong className="font-semibold text-slate-900 dark:text-white bg-indigo-50 dark:bg-indigo-900/20 px-1 rounded" {...props} />,
                            blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-slate-300 dark:border-slate-700 pl-4 italic text-slate-500 my-6" {...props} />,
                          }}
                        >
                          {displayText}
                        </ReactMarkdown>
                      )}
                    </Typewriter>
                  </div>

                  {/* Decorative Footer */}
                  <div className="mt-12 pt-6 border-t border-slate-100 dark:border-slate-800 flex justify-center">
                    <div className="w-8 h-8 rounded-full border border-slate-200 dark:border-slate-700 flex items-center justify-center">
                      <span className="text-xs italic text-slate-400">AI</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Citations Column */}
              <div className="space-y-6">
                <div className="bg-white/80 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur-md transition-colors duration-300">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                    Cited Cases
                  </h3>
                  <ul className="space-y-3">
                    {result.cited_cases.map((caseName, index) => (
                      <li key={index} className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-950/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer border border-slate-200 dark:border-slate-800 hover:border-indigo-500/30 group">
                        <div className="mt-1 w-2 h-2 rounded-full bg-indigo-500 group-hover:bg-indigo-400 transition-colors" />
                        <span className="text-sm text-slate-600 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-200 transition-colors">{caseName}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-slate-50/50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl p-6 transition-colors duration-300 backdrop-blur-sm">
                  <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Disclaimer</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    This tool provides information for educational purposes only and does not constitute legal advice. Always consult with a qualified attorney for specific legal concerns.
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="py-8 border-t border-slate-200 dark:border-slate-800 text-center text-slate-500 dark:text-slate-600 text-sm transition-colors duration-300 z-10 relative bg-white/50 dark:bg-slate-950/50 backdrop-blur-md">
        <p>&copy; {new Date().getFullYear()} TechNiche Legal AI. All rights reserved.</p>
      </footer>
    </div>
  );
}
