"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { motion } from "framer-motion";

export function ThemeToggle() {
    const { resolvedTheme, setTheme } = useTheme();
    // Avoid hydration mismatch by only rendering after mount
    const [mounted, setMounted] = React.useState(false);

    React.useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) {
        return null;
    }

    return (
        <button
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            className="p-2 rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
            aria-label="Toggle theme"
        >
            <div className="relative w-5 h-5">
                <motion.div
                    initial={false}
                    animate={{ scale: resolvedTheme === "dark" ? 0 : 1, rotate: resolvedTheme === "dark" ? 90 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="absolute inset-0 flex items-center justify-center text-slate-800 dark:text-slate-200"
                >
                    <Sun className="w-5 h-5" />
                </motion.div>
                <motion.div
                    initial={false}
                    animate={{ scale: resolvedTheme === "dark" ? 1 : 0, rotate: resolvedTheme === "dark" ? 0 : -90 }}
                    transition={{ duration: 0.2 }}
                    className="absolute inset-0 flex items-center justify-center text-slate-800 dark:text-slate-200"
                >
                    <Moon className="w-5 h-5" />
                </motion.div>
            </div>
        </button>
    );
}
