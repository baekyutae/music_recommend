interface ErrorMessageProps {
    message: string;
}

export default function ErrorMessage({ message }: ErrorMessageProps) {
    return (
        <p className="text-red-400 text-sm mt-2 text-center">{message}</p>
    );
}
