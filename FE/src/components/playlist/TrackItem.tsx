import type { RecommendationItem } from "../../lib/types";

interface TrackItemProps {
    track: RecommendationItem;
}

export default function TrackItem({ track }: TrackItemProps) {
    return (
        <div className="flex items-center gap-4 p-3 rounded-lg hover:bg-slate-800/50 transition-colors group">
            {/* Album cover placeholder */}
            <div className="w-12 h-12 rounded-md bg-slate-700 flex-shrink-0 flex items-center justify-center">
                <span className="text-slate-500 text-xs">♪</span>
            </div>

            {/* Track info */}
            <div className="flex-1 min-w-0">
                <p className="font-semibold text-white truncate">{track.song_name}</p>
                <p className="text-sm text-slate-400 truncate">{track.artist}</p>
            </div>

            {/* Play button */}
            <button className="w-10 h-10 rounded-full border border-slate-600 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:border-emerald-500 hover:text-emerald-500">
                <svg
                    className="w-4 h-4"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path d="M8 5v14l11-7z" />
                </svg>
            </button>
        </div>
    );
}
