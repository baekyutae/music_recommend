import { useState } from "react";
import { fetchRecommendations } from "../lib/api";
import type { RecommendResponse } from "../lib/types";
import SeedInputSection from "../components/input/SeedInputSection";
import AnalyzingScreen from "../components/loading/AnalyzingScreen";
import PlaylistView from "../components/playlist/PlaylistView";

type ViewState = "input" | "loading" | "result";

export default function SongCuratorPage() {
    const [viewState, setViewState] = useState<ViewState>("input");
    const [seedInput, setSeedInput] = useState("");
    const [recommendData, setRecommendData] = useState<RecommendResponse | null>(
        null
    );
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async () => {
        // Clear previous error
        setError(null);

        // Validate input
        const seedId = Number(seedInput.trim());
        if (!seedInput.trim() || isNaN(seedId) || !Number.isInteger(seedId)) {
            setError("현재는 곡 ID(숫자)만 입력할 수 있습니다.");
            return;
        }

        // Start loading
        setViewState("loading");

        try {
            const data = await fetchRecommendations(seedId);
            setRecommendData(data);
            setViewState("result");
        } catch (err) {
            console.error("Recommendation failed:", err);
            setError("추천 요청 중 오류가 발생했습니다.");
            setViewState("input");
        }
    };

    const handleRetry = () => {
        setRecommendData(null);
        setViewState("input");
    };

    // Render based on view state
    if (viewState === "loading") {
        return <AnalyzingScreen />;
    }

    if (viewState === "result" && recommendData) {
        return <PlaylistView data={recommendData} onRetry={handleRetry} />;
    }

    return (
        <SeedInputSection
            seedInput={seedInput}
            onChange={setSeedInput}
            onSubmit={handleSubmit}
            error={error}
        />
    );
}
