import { API_BASE_URL, DEFAULT_K } from "./config";
import type { RecommendResponse } from "./types";

export async function fetchRecommendations(
    seedId: number,
    k: number = DEFAULT_K
): Promise<RecommendResponse> {
    const params = new URLSearchParams({
        seed_id: String(seedId),
        k: String(k),
    });

    const res = await fetch(`${API_BASE_URL}/recommend?${params.toString()}`);

    if (!res.ok) {
        throw new Error(`Recommend API failed: ${res.status}`);
    }

    const data = (await res.json()) as RecommendResponse;
    return data;
}
