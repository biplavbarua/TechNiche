"use client";

import { useState, useEffect, useCallback } from "react";

interface TypewriterProps {
    text: string;
    speed?: number;
    onComplete?: () => void;
    className?: string;
    children: (text: string) => React.ReactNode;
}

/**
 * Line-aware Typewriter
 * 
 * Instead of revealing character-by-character (which breaks markdown table
 * parsing mid-row), this component reveals text LINE-BY-LINE.  Each line
 * is appended whole, so markdown pipe-tables, headings, and list items
 * are always parseable at every intermediate render frame.
 * 
 * For very short text (<200 chars), it falls back to instant reveal.
 */
export function Typewriter({
    text,
    speed = 20,
    onComplete,
    children
}: TypewriterProps) {
    const [displayedLines, setDisplayedLines] = useState(0);

    // Split text into lines, preserving empty lines for paragraph breaks
    const lines = text.split("\n");
    const totalLines = lines.length;

    // Reset when text changes (new analysis)
    useEffect(() => {
        setDisplayedLines(0);
    }, [text]);

    useEffect(() => {
        // For very short text, show immediately
        if (text.length < 200) {
            setDisplayedLines(totalLines);
            if (onComplete) onComplete();
            return;
        }

        if (displayedLines < totalLines) {
            const timeout = setTimeout(() => {
                setDisplayedLines((prev) => prev + 1);
            }, speed);

            return () => clearTimeout(timeout);
        } else if (onComplete) {
            onComplete();
        }
    }, [displayedLines, totalLines, text, speed, onComplete]);

    const visibleText = lines.slice(0, displayedLines).join("\n");

    return <>{children(visibleText)}</>;
}
