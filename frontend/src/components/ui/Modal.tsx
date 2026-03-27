import React from 'react';
import './Modal.css';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  disableClose?: boolean;
}

export function Modal({ isOpen, onClose, title, children, disableClose = false }: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modalOverlay" onClick={() => !disableClose && onClose()}>
      <div className="modalContent" onClick={(e) => e.stopPropagation()}>
        <div className="modalHeader">
          <h2>{title}</h2>
          <button 
            type="button" 
            className="closeBtn" 
            onClick={onClose} 
            disabled={disableClose}
            aria-label="Close modal"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function ModalBody({ children }: { children: React.ReactNode }) {
  return <div className="modalBody">{children}</div>;
}

export function ModalFooter({ children }: { children: React.ReactNode }) {
  return <div className="modalFooter">{children}</div>;
}

export function ModalError({ message }: { message: string }) {
  return <div className="modalError">{message}</div>;
}

export function FormGroup({ label, children }: { label: string, children: React.ReactNode }) {
  return (
    <div className="formGroup">
      <label>{label}</label>
      {children}
    </div>
  );
}
