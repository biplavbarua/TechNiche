"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, BookOpen, Loader2, CheckCircle, AlertCircle, Clock } from "lucide-react";
import { learnFromUrl } from "@/lib/api";

interface LearningModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function LearningModal({ isOpen, onClose }: LearningModalProps) {
    const [url, setUrl] = useState("");
    const [status, setStatus] = useState<"idle" | "queued" | "processing" | "success" | "error">("idle");
    const [message, setMessage] = useState("");

    const isLoading = status === "queued" || status === "processing";

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!url) return;

        setStatus("queued");
        setMessage("Queuing ingestion job...");

        try {
            // learnFromUrl posts to /api/learn/url (202) then polls /api/tasks/{id}
            setStatus("processing");
            setMessage("Fetching case from IndianKanoon API, extracting metadata, and storing embeddings. This may take 30–90 seconds...");

            const result = await learnFromUrl(url);
            setStatus("success");
            // "already ingested" is a success — it's in the KB
            setMessage(result.message || "Successfully added to the knowledge base.");
            setUrl("");
            setTimeout(() => {
                setStatus("idle");
                setMessage("");
                onClose();
            }, 4000);
        } catch (err: unknown) {
            setStatus("error");
            setMessage(err.message || "Failed to learn from URL. Please try again.");
        }
    };

    const getStatusIcon = () => {
        if (status === "success") return <CheckCircle className="w-4 h-4 flex-shrink-0" />;
        if (status === "error") return <AlertCircle className="w-4 h-4 flex-shrink-0" />;
        if (status === "processing") return <Clock className="w-4 h-4 flex-shrink-0 animate-pulse" />;
        return null;
    };

    const getStatusStyle = () => {
        if (status === "success") return "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-500/10";
        if (status === "error") return "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10";
        return "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10";
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={!isLoading ? onClose : undefined}
                        className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50"
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
                    >
                        <div className="bg-white dark:bg-slate-900 w-full max-w-md rounded-2xl shadow-2xl overflow-hidden pointer-events-auto border border-slate-200 dark:border-slate-800">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-indigo-100 dark:bg-indigo-500/20 rounded-lg">
                                            <BookOpen className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                                                Teach the AI
                                            </h3>
                                            <p className="text-sm text-slate-500 dark:text-slate-400">
                                                Add a case from IndianKanoon
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={!isLoading ? onClose : undefined}
                                        disabled={isLoading}
                                        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>

                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                                            IndianKanoon Case URL
                                        </label>
                                        <input
                                            type="url"
                                            value={url}
                                            onChange={(e) => setUrl(e.target.value)}
                                            placeholder="https://indiankanoon.org/doc/1712542/"
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all font-mono text-sm disabled:opacity-50"
                                            required
                                            disabled={isLoading}
                                        />
                                        <p className="mt-1.5 text-xs text-slate-400">
                                            Paste a direct doc URL, e.g.{" "}
                                            <span className="font-mono">indiankanoon.org/doc/257876/</span>
                                        </p>
                                    </div>

                                    {/* Status Messages */}
                                    {message && status !== "idle" && (
                                        <div className={`flex items-start gap-2 text-sm p-3 rounded-lg ${getStatusStyle()}`}>
                                            {getStatusIcon()}
                                            <span>{message}</span>
                                        </div>
                                    )}

                                    {/* Progress bar while processing */}
                                    {isLoading && (
                                        <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                            <div className="h-full bg-indigo-500 rounded-full animate-pulse w-full origin-left" style={{ animation: "progress-indeterminate 2s ease-in-out infinite" }} />
                                        </div>
                                    )}

                                    <div className="pt-2">
                                        <button
                                            type="submit"
                                            disabled={isLoading}
                                            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                                        >
                                            {isLoading ? (
                                                <>
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                    {status === "queued" ? "Queuing..." : "Processing..."}
                                                </>
                                            ) : (
                                                "Add to Knowledge Base"
                                            )}
                                        </button>
                                    </div>
                                </form>
                            </div>
                            <div className="bg-slate-50 dark:bg-slate-950/50 px-6 py-4 border-t border-slate-100 dark:border-slate-800">
                                <p className="text-xs text-slate-500 text-center">
                                    The case will be fetched via IndianKanoon API, AI-parsed, chunked, and embedded into the knowledge base. Processing takes 30–90 seconds.
                                </p>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
