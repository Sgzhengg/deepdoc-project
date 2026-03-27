import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastProps {
  type: ToastType;
  message: string;
  duration?: number;
  onClose?: () => void;
}

const Toast: React.FC<ToastProps> = ({
  type,
  message,
  duration = 3000,
  onClose,
}) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        setVisible(false);
        setTimeout(() => onClose?.(), 300);
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const handleClose = () => {
    setVisible(false);
    setTimeout(() => onClose?.(), 300);
  };

  const typeConfig = {
    success: {
      icon: <CheckCircle size={20} className="text-green-400" />,
      bgColor: 'bg-green-600/20',
      borderColor: 'border-green-600/50',
    },
    error: {
      icon: <XCircle size={20} className="text-red-400" />,
      bgColor: 'bg-red-600/20',
      borderColor: 'border-red-600/50',
    },
    warning: {
      icon: <AlertCircle size={20} className="text-yellow-400" />,
      bgColor: 'bg-yellow-600/20',
      borderColor: 'border-yellow-600/50',
    },
    info: {
      icon: <Info size={20} className="text-blue-400" />,
      bgColor: 'bg-blue-600/20',
      borderColor: 'border-blue-600/50',
    },
  };

  const config = typeConfig[type];

  return (
    <div
      className={`
        fixed top-4 right-4 z-50
        flex items-center gap-3 px-4 py-3
        ${config.bgColor} ${config.borderColor}
        border rounded-lg shadow-lg
        transition-all duration-300
        ${visible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-full'}
      `}
    >
      {config.icon}
      <span className="text-sm text-gray-200">{message}</span>
      <button
        onClick={handleClose}
        className="p-1 hover:bg-black/20 rounded transition-colors"
      >
        <X size={16} className="text-gray-400" />
      </button>
    </div>
  );
};

export default Toast;
