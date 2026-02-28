import { useApp } from '../hooks/useAppContext';
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react';

export default function ToastContainer() {
    const { toasts } = useApp();

    const icons = {
        success: <CheckCircle size={16} />,
        error: <AlertCircle size={16} />,
        info: <Info size={16} />,
    };

    if (toasts.length === 0) return null;

    return (
        <div className="toast-container">
            {toasts.map(toast => (
                <div
                    key={toast.id}
                    className={`toast ${toast.type}${toast.exiting ? ' exiting' : ''}`}
                    role="alert"
                >
                    {icons[toast.type]}
                    <span>{toast.message}</span>
                </div>
            ))}
        </div>
    );
}
