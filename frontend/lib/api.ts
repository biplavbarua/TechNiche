export interface AnalysisResult {
    analysis: string;
    cited_cases: string[];
    cited_cases_details?: {
        title: string;
        url: string;
        snippet: string;
    }[];
    relevance_quality?: "high" | "low" | "none";
    llm_cited_cases?: string[];
    citation_verification?: {
        grounded: string[];
        ungrounded: string[];
        confidence: "high" | "low" | "general";
        correction_applied?: boolean;
    };
}

export interface CrawlResult {
    message: string;
    cases: { url: string; title: string }[];
}

const getBackendUrl = () => {
    // In development, talk directly to the Python backend to avoid Proxy issues.
    if (process.env.NODE_ENV === "development") {
        return "http://localhost:8000";
    }
    // In production, use the explicitly set backend URL
    return process.env.NEXT_PUBLIC_API_URL || "";
};

export async function analyzeIdea(idea: string): Promise<AnalysisResult> {
    const backendUrl = getBackendUrl();
    try {
        const response = await fetch(`${backendUrl}/api/analyze`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ idea }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || "Analysis failed");
        }

        return await response.json();
    } catch (error) {
        console.error("API Error:", error);
        throw error;
    }
}

export async function learnFromUrl(url: string): Promise<CrawlResult> {
    const backendUrl = getBackendUrl();
    try {
        const response = await fetch(`${backendUrl}/api/crawl`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ url }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || "Learning failed");
        }

        return await response.json();
    } catch (error) {
        console.error("API Error:", error);
        throw error;
    }
}
