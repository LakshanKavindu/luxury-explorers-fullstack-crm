import React, { useState, useEffect } from 'react';
import { createContact, updateContact } from '../api/contactApi';
import type { Contact } from '../types/crm';
import { Modal, ModalBody, ModalFooter, ModalError, FormGroup } from './ui/Modal';

interface ContactModalProps {
  isOpen: boolean;
  companyId: string;
  contact?: Contact;
  onClose: (wasSaved: boolean) => void;
}

export default function ContactModal({ isOpen, companyId, contact, onClose }: ContactModalProps) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [role, setRole] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  useEffect(() => {
    if (contact) {
      setFullName(contact.full_name);
      setEmail(contact.email);
      setPhone(contact.phone || '');
      setRole(contact.role || '');
    } else {
      setFullName('');
      setEmail('');
      setPhone('');
      setRole('');
    }
    setError(null);
    setFieldErrors({});
  }, [contact, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim()) {
      setError("Name and Email are required.");
      return;
    }

    setLoading(true);
    setError(null);
    setFieldErrors({});

    try {
      const data: Partial<Contact> = {
        full_name: fullName,
        email,
        phone,
        role,
      };

      if (contact?.id) {
        await updateContact(contact.id, data);
      } else {
        data.company = companyId;
        await createContact(data);
      }
      onClose(true);
    } catch (err: any) {
      console.error(err);
      
      // Parse detailed validation feedback from DRF
      const errors = err.response?.data?.errors;
      if (errors && typeof errors === 'object') {
        setFieldErrors(errors);
        setError("Please correct the highlighted errors.");
      } else {
        const msg = err.response?.data?.message || err.message;
        setError(msg || "An error occurred while saving the contact.");
      }
    } finally {
      setLoading(false);
    }
  };

  const title = contact ? 'Edit Contact' : 'Add New Contact';

  return (
    <Modal isOpen={isOpen} onClose={() => onClose(false)} title={title} disableClose={loading}>
      <form onSubmit={handleSubmit}>
        <ModalBody>
          {error && <ModalError message={error} />}

          <FormGroup label="Full Name *">
            <input 
              type="text" 
              className={`formInput ${fieldErrors.full_name ? 'invalid' : ''}`}
              placeholder="Jane Doe"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoFocus
              disabled={loading}
              required
            />
            {fieldErrors.full_name && <span style={{color: '#ef4444', fontSize: '13px'}}>{fieldErrors.full_name[0]}</span>}
          </FormGroup>

          <FormGroup label="Email Address *">
            <input 
              type="email" 
              className={`formInput ${fieldErrors.email ? 'invalid' : ''}`}
              placeholder="jane@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              required
            />
            {fieldErrors.email && <span style={{color: '#ef4444', fontSize: '13px'}}>{fieldErrors.email[0]}</span>}
          </FormGroup>

          <FormGroup label="Phone Number">
            <input 
              type="tel" 
              className={`formInput ${fieldErrors.phone ? 'invalid' : ''}`}
              placeholder="8 to 15 digits"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={loading}
            />
            {fieldErrors.phone && <span style={{color: '#ef4444', fontSize: '13px'}}>{fieldErrors.phone[0]}</span>}
          </FormGroup>

          <FormGroup label="Job Role">
            <input 
              type="text" 
              className={`formInput ${fieldErrors.role ? 'invalid' : ''}`}
              placeholder="e.g. Lead Engineer"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              disabled={loading}
            />
            {fieldErrors.role && <span style={{color: '#ef4444', fontSize: '13px'}}>{fieldErrors.role[0]}</span>}
          </FormGroup>
        </ModalBody>

        <ModalFooter>
          <button type="button" className="cancelBtn" onClick={() => onClose(false)} disabled={loading}>
            Cancel
          </button>
          <button type="submit" className="saveBtn" disabled={loading}>
            {loading ? 'Saving...' : 'Save Contact'}
          </button>
        </ModalFooter>
      </form>
    </Modal>
  );
}
