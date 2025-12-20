import { ButtonHTMLAttributes } from "react";

interface SecondaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    children: React.ReactNode;
}

export default function SecondaryButton({
    children,
    className = "",
    ...props
}: SecondaryButtonProps) {
    return (
        <button
            className={`w-full py-3 px-6 border border-slate-600 hover:border-slate-400 text-slate-300 hover:text-white font-medium rounded-full transition-colors duration-200 ${className}`}
            {...props}
        >
            {children}
        </button>
    );
}
