import Header from "../layout/Header";
import PrimaryButton from "../common/PrimaryButton";
import ErrorMessage from "../common/ErrorMessage";

interface SeedInputSectionProps {
    seedInput: string;
    onChange: (value: string) => void;
    onSubmit: () => void;
    error: string | null;
}

export default function SeedInputSection({
    seedInput,
    onChange,
    onSubmit,
    error,
}: SeedInputSectionProps) {
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") {
            onSubmit();
        }
    };

    return (
        <div className="flex flex-col items-center">
            <Header />

            <div className="w-full max-w-md space-y-4">
                <input
                    type="text"
                    value={seedInput}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="시드 곡 ID를 입력하세요 (예: 123456)"
                    className="w-full px-6 py-4 bg-slate-800 border border-slate-700 rounded-full text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                />

                {error && <ErrorMessage message={error} />}

                <PrimaryButton onClick={onSubmit}>추천받기</PrimaryButton>
            </div>
        </div>
    );
}
