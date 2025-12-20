interface PlaylistHeaderProps {
    seedSongName: string;
}

export default function PlaylistHeader({ seedSongName }: PlaylistHeaderProps) {
    return (
        <div className="text-center mb-8">
            <h2 className="text-2xl font-bold mb-2">
                <span className="mr-2">✨</span>
                당신을 위한 플레이리스트
            </h2>
            <p className="text-slate-400">
                "{seedSongName}" 기반 추천
            </p>
        </div>
    );
}
