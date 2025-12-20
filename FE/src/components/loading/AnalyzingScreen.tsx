import Spinner from "../common/Spinner";

export default function AnalyzingScreen() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[400px] space-y-8">
            <Spinner />

            <div className="text-center space-y-3">
                <h2 className="text-2xl font-semibold text-white">
                    당신의 Vibe를 분석 중입니다...
                </h2>
                <p className="text-slate-400 text-sm">
                    13만 곡의 데이터베이스와 대조 중...
                </p>
            </div>
        </div>
    );
}
