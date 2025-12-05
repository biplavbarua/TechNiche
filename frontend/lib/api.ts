export interface AnalysisResult {
    analysis: string;
    cited_cases: string[];
}

export async function analyzeIdea(idea: string): Promise<AnalysisResult> {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    try {
        const response = await fetch(`${backendUrl}/api/analyze`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ idea }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Analysis failed");
        }

        return await response.json();
    } catch (error) {
        console.error("API Error:", error);
        throw error;
    }
}
