"use client";

import { useState, useEffect } from "react";

interface TypewriterProps {
    text: string;
    speed?: number;
    onComplete?: () => void;
    className?: string;
    children: (text: string) => React.ReactNode;
}

export function Typewriter({
    text,
    speed = 5,
    onComplete,
    children
}: TypewriterProps) {
    const [displayedText, setDisplayedText] = useState("");
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        // Reset if text changes completely (new analysis)
        if (text !== displayedText && currentIndex === 0) {
            setDisplayedText("");
        }
    }, [text]);

    useEffect(() => {
        if (currentIndex < text.length) {
            const timeout = setTimeout(() => {
                setDisplayedText((prev) => prev + text[currentIndex]);
                setCurrentIndex((prev) => prev + 1);
            }, speed);

            return () => clearTimeout(timeout);
        } else if (onComplete) {
            onComplete();
        }
    }, [currentIndex, text, speed, onComplete]);

    // If text is extremely long, we might want to chunk it to avoid thousands of re-renders
    // For now, character-by-character is standard typewriting.

    return <>{children(displayedText)}</>;
}
