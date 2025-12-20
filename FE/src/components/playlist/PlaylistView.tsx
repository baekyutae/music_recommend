import type { RecommendResponse } from "../../lib/types";
import PlaylistHeader from "./PlaylistHeader";
import TrackItem from "./TrackItem";
import PrimaryButton from "../common/PrimaryButton";
import SecondaryButton from "../common/SecondaryButton";

interface PlaylistViewProps {
    data: RecommendResponse;
    onRetry: () => void;
}

export default function PlaylistView({ data, onRetry }: PlaylistViewProps) {
    const handleSpotifyClick = () => {
        alert("플레이리스트 공유 기능은 추후 추가 예정입니다.");
    };

    return (
        <div className="space-y-6">
            <PlaylistHeader seedSongName={data.seed.song_name} />

            {/* Playlist card */}
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-6 border border-slate-700">
                <h3 className="text-xl font-bold text-white mb-2">K-Pop Hypersonic</h3>
                <p className="text-slate-400 text-sm mb-4">
                    당신의 심장을 뛰게 할 에너제틱한 K-Pop 히트곡 모음.
                </p>

                <PrimaryButton onClick={handleSpotifyClick} className="mb-0">
                    <span className="flex items-center justify-center gap-2">
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
                        </svg>
                        Spotify 플레이리스트로 열기
                    </span>
                </PrimaryButton>
            </div>

            {/* Track list */}
            <div className="bg-slate-900/50 rounded-2xl border border-slate-800">
                <div className="max-h-[400px] overflow-y-auto p-2">
                    {data.items.map((track) => (
                        <TrackItem key={track.song_id} track={track} />
                    ))}
                </div>
            </div>

            {/* Retry button */}
            <SecondaryButton onClick={onRetry}>
                다른 노래로 다시 추천받기
            </SecondaryButton>
        </div>
    );
}
