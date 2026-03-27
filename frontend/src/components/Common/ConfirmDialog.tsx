import React from 'react';
import Modal from './Modal';
import { AlertTriangle } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'danger' | 'warning' | 'info';
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = '确认',
  cancelText = '取消',
  type = 'danger',
}) => {
  const handleConfirm = async () => {
    await onConfirm();
    onClose();
  };

  const typeConfig = {
    danger: {
      icon: <AlertTriangle size={32} className="text-red-400" />,
      confirmClass: 'bg-red-600 hover:bg-red-700 text-white',
    },
    warning: {
      icon: <AlertTriangle size={32} className="text-yellow-400" />,
      confirmClass: 'bg-yellow-600 hover:bg-yellow-700 text-white',
    },
    info: {
      icon: <AlertTriangle size={32} className="text-blue-400" />,
      confirmClass: 'bg-blue-600 hover:bg-blue-700 text-white',
    },
  };

  const config = typeConfig[type];

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm">
      <div className="text-center">
        {config.icon}
        <h3 className="text-lg font-semibold text-chat-text mt-4 mb-2">
          {title}
        </h3>
        <p className="text-sm text-gray-400 mb-6">{message}</p>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-chat-input hover:bg-chat-bg-secondary text-chat-text rounded-lg border border-chat-border transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            className={`flex-1 px-4 py-2 rounded-lg transition-colors ${config.confirmClass}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default ConfirmDialog;
