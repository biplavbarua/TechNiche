export interface AnalysisResult {
    analysis: string;
    cited_cases: string[];
}

export interface CrawlResult {
    message: string;
    cases: { url: string; title: string }[];
}

const getBackendUrl = () => {
    // Use relative path to leverage Next.js rewrites
    // This allows the browser to call /api/... on the same domain,
    // and Next.js will proxy it to the actual backend.
    return "";
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
