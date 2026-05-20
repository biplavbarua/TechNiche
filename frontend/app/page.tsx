"use client";

import { useState, useRef } from "react";
import { analyzeIdea, AnalysisResult } from "../lib/api";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Typewriter } from "@/components/typewriter";
import { TableCards } from "@/components/markdown-table-cards";
import { ArrowRight, Scale, AlertTriangle, Search, Github, Linkedin, Download, FileText, Briefcase, Building2, BookOpen } from "lucide-react";
import { LearningModal } from "@/components/learning-modal";

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
        setError("Failed to connect to the Server. Please check your internet connection or try again later. If you are the developer, ensure the Backend URL is set correctly.");
      } else {
        setError(err.message || "Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 font-sans relative selection:bg-blue-200">
      <LearningModal isOpen={isLearningModalOpen} onClose={() => setIsLearningModalOpen(false)} />

      {/* Enterprise Header */}
      <header className="fixed top-0 w-full z-50 border-b-2 border-slate-200 bg-white shadow-sm print:hidden">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-sm shadow-sm">
              <Scale className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-extrabold tracking-tight text-slate-900">
              TechNiche<span className="text-blue-600">Legal</span>
            </span>
            <span className="ml-3 px-2 py-1 text-[0.65rem] font-bold uppercase tracking-widest text-slate-700 bg-slate-100 rounded-sm border border-slate-200">
              Innovators Edition
            </span>
          </div>
          <nav className="flex items-center gap-6 text-sm font-bold text-slate-600">
            <button
              onClick={() => setIsLearningModalOpen(true)}
              className="flex items-center gap-2 hover:text-blue-600 transition-colors hidden md:flex"
            >
              <BookOpen className="w-4 h-4" /> Knowledge Base
            </button>
            <a
              href="/solutions"
              className="hover:text-blue-600 transition-colors flex items-center gap-2 hidden lg:flex"
            >
              <Briefcase className="w-4 h-4" /> Solutions
            </a>
            <a
              href="/enterprise"
              className="hover:text-blue-600 transition-colors flex items-center gap-2 hidden lg:flex"
            >
              <Building2 className="w-4 h-4" /> Enterprise
            </a>
            <div className="h-5 w-[2px] bg-slate-200 mx-1 hidden md:block" />
            <a
              href="https://github.com/biplavbarua/TechNiche"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 transition-colors"
              title="View Source on GitHub"
            >
              <Github className="w-5 h-5" />
            </a>
            <a
              href="https://www.linkedin.com/in/biplavbarua/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 transition-colors"
              title="Connect on LinkedIn"
            >
              <Linkedin className="w-5 h-5" />
            </a>
          </nav>
        </div>
      </header>

      <main className="pt-32 pb-24 px-6 max-w-6xl mx-auto z-10 relative print:pt-0 print:pb-0">
        <div className="text-center mb-16 space-y-6 print:hidden">
          <h1 className="text-5xl md:text-6xl font-black tracking-tight text-slate-900">
            Stop Guessing. Know if
            <br className="hidden md:block" />
            <span className="text-blue-600 block mt-2">Your Idea is Protected.</span>
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto font-medium">
            Innovate with confidence. TechNiche Legal AI instantly cross-references your product ideas against millions of existing patents, so you can build without the looming threat of IP liability.
          </p>
        </div>

        <div className="bg-white border-2 border-slate-200 shadow-[0_4px_20px_rgb(0,0,0,0.03)] p-2 transition-all duration-300 print:hidden focus-within:border-blue-500 focus-within:shadow-[0_8px_30px_rgba(37,99,235,0.1)] mx-auto max-w-4xl">
          <div className="relative">
            <textarea
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              placeholder="Describe your product idea or technical innovation to instantly check for patent conflicts..."
              className="w-full h-40 bg-slate-50 p-6 text-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:bg-white transition-colors resize-none border border-slate-100 font-medium"
            />
            <div className="absolute bottom-4 right-4 flex items-center gap-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest hidden sm:block">
                Bank-Grade SSL
              </span>
              <button
                onClick={handleAnalyze}
                disabled={loading || !idea.trim()}
                className="flex items-center gap-2 px-8 py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-extrabold text-sm uppercase tracking-wider transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
              >
                {loading ? (
                  <span className="flex items-center gap-3">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Executing Scan
                  </span>
                ) : (
                  <>
                    Check Conflicts <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-8 p-6 bg-red-50 border-l-4 border-red-600 text-red-800 flex items-start gap-4 shadow-sm mx-auto max-w-4xl">
            <AlertTriangle className="w-6 h-6 flex-shrink-0 text-red-600 mt-0.5" />
            <div>
              <h3 className="text-sm font-extrabold uppercase tracking-wider mb-1">System Exception</h3>
              <p className="text-sm font-semibold">{error}</p>
            </div>
          </div>
        )}

        {result && (
          <div
            className="mt-20 grid grid-cols-1 lg:grid-cols-12 gap-10 print:block print:mt-0"
            ref={containerRef}
          >
            {/* Report Column */}
            <div className="lg:col-span-8 space-y-8">
              <div className="bg-white border-2 border-slate-200 p-8 md:p-12 shadow-sm relative">
                
                <div className="border-b-2 border-slate-200 pb-6 mb-8 flex flex-col md:flex-row md:justify-between md:items-end gap-4 print:border-b-0 print:pb-4">
                  <div>
                    <div className="flex items-center gap-3 mb-3">
                      <span className="px-2.5 py-1 bg-red-100 text-red-800 text-[0.65rem] font-black uppercase tracking-widest border border-red-200">
                        Confidential
                      </span>
                      <span className="text-xs font-extrabold text-slate-400 uppercase tracking-widest">
                        ID: {new Date().toISOString().split('T')[0].replace(/-/g, '')}-{Math.random().toString(36).substring(2, 10).toUpperCase()}
                      </span>
                    </div>
                    <h2 className="text-3xl font-black text-slate-900 tracking-tight leading-tight">
                      Liability & Compliance Audit
                    </h2>
                  </div>
                  <div className="flex gap-3 print:hidden">
                    <button
                      onClick={handleDownloadPDF}
                      className="flex items-center gap-2 px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs uppercase tracking-wider transition-colors border border-slate-200 shadow-sm"
                      title="Export PDF"
                    >
                      <Download className="w-4 h-4" /> Export Document
                    </button>
                  </div>
                </div>

                <div className="legal-prose max-w-none text-slate-800">
                  <Typewriter text={result.analysis} speed={8}>
                    {(displayText) => (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h1: ({ node, ...props }) => <h1 className="text-2xl font-black mt-10 mb-6 pb-2 border-b-2 border-slate-900 text-slate-900 uppercase tracking-tight" {...props} />,
                          h2: ({ node, ...props }) => <h2 className="text-xl font-extrabold mt-8 mb-4 text-slate-900" {...props} />,
                          h3: ({ node, ...props }) => <h3 className="text-lg font-bold mt-6 mb-3 text-slate-800" {...props} />,
                          ul: ({ node, ...props }) => <ul className="list-square pl-6 space-y-2 mb-6" {...props} />,
                          ol: ({ node, ...props }) => <ol className="list-decimal pl-6 space-y-2 mb-6 font-semibold text-slate-700" {...props} />,
                          li: ({ node, ...props }) => <li className="pl-2" {...props} />,
                          p: ({ node, ...props }) => <p className="mb-5 leading-relaxed text-lg" {...props} />,
                          strong: ({ node, children, ...props }) => {
                            const text = typeof children === 'string' ? children : '';
                            const upper = text.toUpperCase();
                            if (upper === 'HIGH' || upper === 'HIGH RISK') {
                              return <span className="risk-badge risk-high shadow-sm">■ {children}</span>;
                            }
                            if (upper === 'MEDIUM' || upper === 'MEDIUM RISK' || upper.includes('MEDIUM')) {
                              return <span className="risk-badge risk-medium shadow-sm">■ {children}</span>;
                            }
                            if (upper === 'LOW' || upper === 'LOW RISK') {
                              return <span className="risk-badge risk-low shadow-sm">■ {children}</span>;
                            }
                            return <strong className="font-extrabold text-slate-900" {...props}>{children}</strong>;
                          },
                          blockquote: ({ node, ...props }) => <blockquote className="bg-slate-50 border-l-4 border-blue-600 p-6 my-6 font-semibold text-slate-700 shadow-inner" {...props} />,
                          hr: ({ node, ...props }) => <hr className="border-t-2 border-slate-200 my-10" {...props} />,
                          a: ({ node, ...props }) => <a target="_blank" rel="noopener noreferrer" className="text-blue-600 font-extrabold underline decoration-blue-200 underline-offset-4 hover:decoration-blue-600 transition-colors" {...props} />,
                          code: ({ node, ...props }) => <code className="bg-slate-100 text-slate-900 px-1.5 py-0.5 text-sm font-bold font-mono border border-slate-200 shadow-sm" {...props} />,
                          table: ({ node, children, ...props }) => <TableCards>{children}</TableCards>,
                          thead: ({ node, ...props }) => <thead {...props} />,
                          tbody: ({ node, ...props }) => <tbody {...props} />,
                          tr: ({ node, ...props }) => <tr {...props} />,
                          th: ({ node, ...props }) => <th {...props} />,
                          td: ({ node, ...props }) => <td {...props} />,
                        }}
                      >
                        {displayText}
                      </ReactMarkdown>
                    )}
                  </Typewriter>
                </div>
              </div>
            </div>

            {/* Citations Column */}
            <div className="lg:col-span-4 space-y-8 print:hidden">
              <div className="bg-slate-50 border-2 border-slate-200 p-6 print:shadow-none print:mt-10 lg:sticky lg:top-24">
                <h3 className="text-sm font-black text-slate-900 mb-6 flex items-center gap-2 uppercase tracking-widest border-b-2 border-slate-200 pb-4">
                  <Search className="w-4 h-4 text-blue-600" />
                  Precedent Database
                </h3>
                <div className="space-y-4">
                  {result.relevance_quality === "none" && (
                    <div className="p-4 bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold leading-relaxed">
                      <div className="flex items-start gap-2 mb-1">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600" />
                        <span className="font-black uppercase tracking-wider text-[0.65rem]">General Analysis</span>
                      </div>
                      <p className="pl-6">Our precedent database did not contain cases directly relevant to this query. The analysis below is based on general legal knowledge and established Indian law principles.</p>
                    </div>
                  )}
                  {result.cited_cases_details && result.cited_cases_details.length > 0 ? (
                    result.cited_cases_details.map((caseInfo, index) => (
                      <a href={caseInfo.url} target="_blank" rel="noopener noreferrer" key={index} className="flex flex-col gap-2 p-5 bg-white border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow-md transition-all cursor-pointer group rounded-none block">
                        <div className="flex items-start gap-4">
                          <FileText className="w-5 h-5 mt-0.5 text-slate-400 group-hover:text-blue-600 transition-colors flex-shrink-0" />
                          <span className="text-sm font-bold text-slate-800 leading-snug group-hover:text-blue-600 transition-colors">{caseInfo.title}</span>
                        </div>
                        {caseInfo.snippet && (
                          <div className="pl-9 text-xs text-slate-600 italic border-l-2 border-slate-100 ml-2">
                            "{caseInfo.snippet}..."
                          </div>
                        )}
                      </a>
                    ))
                  ) : result.cited_cases && result.cited_cases[0] === "General Legal Principles" ? (
                    <div className="p-5 bg-white border border-slate-200 shadow-sm">
                      <div className="flex items-start gap-4">
                        <Scale className="w-5 h-5 mt-0.5 text-slate-400 flex-shrink-0" />
                        <div>
                          <span className="text-sm font-bold text-slate-800 leading-snug">General Legal Principles</span>
                          <p className="text-xs text-slate-500 mt-1">Analysis is based on established statutes and legal principles rather than specific case precedents from our database.</p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <ul className="space-y-4">
                      {result.cited_cases && result.cited_cases.map((caseName, index) => (
                        <li key={index} className="flex items-start gap-4 p-5 bg-white border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow-md transition-all cursor-pointer group rounded-none">
                          <FileText className="w-5 h-5 mt-0.5 text-slate-400 group-hover:text-blue-600 transition-colors flex-shrink-0" />
                          <span className="text-sm font-bold text-slate-800 leading-snug">{caseName}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {result.llm_cited_cases && result.llm_cited_cases.length > 0 && (
                    <div className="mt-6 pt-4 border-t border-slate-100">
                      <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">
                        Cases Referenced in Analysis
                      </h4>
                      <ul className="space-y-3">
                        {result.llm_cited_cases.map((caseName, index) => (
                          <li key={`llm-case-${index}`} className="flex items-start gap-3 p-4 bg-slate-50 border border-slate-200 shadow-sm rounded-none">
                            <Scale className="w-4 h-4 mt-0.5 text-blue-500 flex-shrink-0" />
                            <span className="text-sm font-bold text-slate-800 leading-snug">{caseName}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Citation Confidence Badge — Fix 3 */}
                {result.citation_verification && result.citation_verification.confidence !== "general" && (
                  <div className="mt-6 pt-4 border-t border-slate-100">
                    <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                      <Search className="w-3.5 h-3.5" />
                      Citation Confidence
                    </h4>
                    <div className={`p-4 rounded-none border text-xs font-semibold leading-relaxed ${
                      result.citation_verification.ungrounded.length === 0
                        ? "bg-green-50 border-green-200 text-green-800"
                        : result.citation_verification.grounded.length > 0
                        ? "bg-amber-50 border-amber-200 text-amber-800"
                        : "bg-red-50 border-red-200 text-red-800"
                    }`}>
                      <div className="flex items-center gap-2 mb-2 font-black uppercase tracking-wider text-[0.65rem]">
                        {result.citation_verification.ungrounded.length === 0
                          ? "✓ All Citations Verified"
                          : result.citation_verification.correction_applied
                          ? "⚡ Auto-Corrected"
                          : "⚠ Partial Verification"}
                      </div>
                      <p>
                        <span className="font-bold">{result.citation_verification.grounded.length}</span> grounded
                        {result.citation_verification.ungrounded.length > 0 && (
                          <> · <span className="font-bold">{result.citation_verification.ungrounded.length}</span> unverified</>
                        )}
                        {result.citation_verification.correction_applied && (
                          <> · hallucinated references removed automatically</>
                        )}
                      </p>
                    </div>
                  </div>
                )}

                <div className="mt-8 pt-6 border-t border-slate-200">
                  <h3 className="text-xs font-black uppercase tracking-widest mb-3 flex items-center gap-2 text-slate-600">
                    <AlertTriangle className="w-4 h-4 text-orange-500" />
                    Legal Disclaimer
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed font-semibold">
                    This compliance assessment leverages natural language processing against Indian Judiciary records. It does not replace certified legal counsel. Do not execute commercial actions based solely on this automated output. Consult your legal representative.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="py-10 border-t-2 border-slate-200 text-center text-slate-500 text-xs mt-20 print:hidden bg-white font-bold tracking-widest uppercase">
        <p>TechNiche Global Legal Solutions &copy; {new Date().getFullYear()}. Automated Enterprise Edition.</p>
      </footer>
    </div>
  );
}
