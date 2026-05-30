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

export interface TaskStatus {
    task_id: string;
    status: "pending" | "running" | "done" | "failed";
    message?: string;
    error?: string;
    url?: string;
    file_name?: string;
    ingested_count?: number;
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

/**
 * Poll a task until it reaches a terminal state (done | failed).
 * Rejects if the task fails or if maxAttempts is exceeded.
 */
async function pollTask(
    taskId: string,
    intervalMs = 3000,
    maxAttempts = 60
): Promise<TaskStatus> {
    const backendUrl = getBackendUrl();
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        await new Promise((r) => setTimeout(r, intervalMs));
        const res = await fetch(`${backendUrl}/api/tasks/${taskId}`);
        if (!res.ok) throw new Error("Failed to poll task status.");
        const task: TaskStatus = await res.json();
        if (task.status === "done") return task;
        if (task.status === "failed") throw new Error(task.error || "Ingestion failed.");
    }
    throw new Error("Timed out waiting for ingestion to complete.");
}

/**
 * Submit a URL for ingestion and poll until done.
 * The backend returns 202 immediately; this function awaits completion.
 */
export async function learnFromUrl(url: string): Promise<TaskStatus> {
    const backendUrl = getBackendUrl();
    const response = await fetch(`${backendUrl}/api/learn/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to queue URL for learning.");
    }

    const { task_id } = await response.json();
    return pollTask(task_id);
}

/**
 * Submit a crawl job and poll until done.
 */
export async function crawlAndLearn(url: string): Promise<TaskStatus> {
    const backendUrl = getBackendUrl();
    const response = await fetch(`${backendUrl}/api/crawl`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to queue crawl job.");
    }

    const { task_id } = await response.json();
    return pollTask(task_id);
}
