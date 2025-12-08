"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, BookOpen, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { learnFromUrl } from "@/lib/api";

interface LearningModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function LearningModal({ isOpen, onClose }: LearningModalProps) {
    const [url, setUrl] = useState("");
    const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
    const [message, setMessage] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!url) return;

        setStatus("loading");
        setMessage("");

        try {
            const result = await learnFromUrl(url);
            setStatus("success");
            setMessage(result.message);
            setUrl("");
            setTimeout(() => {
                setStatus("idle");
                setMessage("");
                onClose();
            }, 3000);
        } catch (err: any) {
            setStatus("error");
            setMessage(err.message || "Failed to learn from URL");
        }
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
                        onClick={onClose}
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
                                                Add knowledge from Indian Kanoon
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={onClose}
                                        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>

                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                                            Case URL (Search Result)
                                        </label>
                                        <input
                                            type="url"
                                            value={url}
                                            onChange={(e) => setUrl(e.target.value)}
                                            placeholder="https://indiankanoon.org/search/..."
                                            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all font-mono text-sm"
                                            required
                                        />
                                    </div>

                                    {/* Status Messages */}
                                    {status === "error" && (
                                        <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 p-3 rounded-lg">
                                            <AlertCircle className="w-4 h-4" />
                                            {message}
                                        </div>
                                    )}
                                    {status === "success" && (
                                        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-500/10 p-3 rounded-lg">
                                            <CheckCircle className="w-4 h-4" />
                                            {message}
                                        </div>
                                    )}

                                    <div className="pt-2">
                                        <button
                                            type="submit"
                                            disabled={status === "loading"}
                                            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                                        >
                                            {status === "loading" ? (
                                                <>
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                    Crawling & Learning...
                                                </>
                                            ) : (
                                                "Start Learning"
                                            )}
                                        </button>
                                    </div>
                                </form>
                            </div>
                            <div className="bg-slate-50 dark:bg-slate-950/50 px-6 py-4 border-t border-slate-100 dark:border-slate-800">
                                <p className="text-xs text-slate-500 text-center">
                                    This will crawl the URL, extract cases, generating embeddings, and update the memory bank instantly.
                                </p>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
