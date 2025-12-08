export interface AnalysisResult {
    analysis: string;
    cited_cases: string[];
}

export interface CrawlResult {
    message: string;
    cases: { url: string; title: string }[];
}

const getBackendUrl = () => {
    // Ensure no trailing slash
    let url = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    if (url.endsWith("/")) {
        url = url.slice(0, -1);
    }
    return url;
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
