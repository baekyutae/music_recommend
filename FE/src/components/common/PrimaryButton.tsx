import { ButtonHTMLAttributes } from "react";

interface PrimaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    children: React.ReactNode;
}

export default function PrimaryButton({
    children,
    className = "",
    ...props
}: PrimaryButtonProps) {
    return (
        <button
            className={`w-full py-3 px-6 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-full transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
            {...props}
        >
            {children}
        </button>
    );
}
