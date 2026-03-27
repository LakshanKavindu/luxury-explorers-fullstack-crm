import React, { useState, useEffect } from 'react';
import { createCompany, updateCompany } from '../api/companyApi';
import type { Company } from '../types/crm';
import { Modal, ModalBody, ModalFooter, ModalError, FormGroup } from './ui/Modal';
import './CompanyModal.css';

interface CompanyModalProps {
  isOpen: boolean;
  company?: Company;
  onClose: (wasSaved: boolean) => void;
}

export default function CompanyModal({ isOpen, company, onClose }: CompanyModalProps) {
  const [name, setName] = useState('');
  const [industry, setIndustry] = useState('');
  const [country, setCountry] = useState('');
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (company) {
      setName(company.name);
      setIndustry(company.industry || '');
      setCountry(company.country || '');
      setLogoPreview(company.logo_url);
    } else {
      setName('');
      setIndustry('');
      setCountry('');
      setLogoPreview(null);
    }
    setLogoFile(null);
    setError(null);
  }, [company, isOpen]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setLogoFile(file);
      setLogoPreview(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Company Name is required.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('name', name);
      if (industry) formData.append('industry', industry);
      if (country) formData.append('country', country);
      if (logoFile) formData.append('logo', logoFile);

      if (company?.id) {
        await updateCompany(company.id, formData);
      } else {
        await createCompany(formData);
      }
      onClose(true);
    } catch (err: any) {
      console.error(err);
      const serverErr = err.response?.data?.errors?.name?.[0] || err.response?.data?.message || err.message;
      setError(serverErr || "An error occurred while saving the company.");
    } finally {
      setLoading(false);
    }
  };

  const title = company ? 'Edit Company' : 'Add New Company';

  return (
    <Modal isOpen={isOpen} onClose={() => onClose(false)} title={title} disableClose={loading}>
      <form onSubmit={handleSubmit}>
        <ModalBody>
          {error && <ModalError message={error} />}

          <FormGroup label="Company Name *">
            <input 
              type="text" 
              className="formInput" 
              placeholder="Acme Corp"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              disabled={loading}
            />
          </FormGroup>

          <FormGroup label="Industry">
            <input 
              type="text" 
              className="formInput"
              placeholder="e.g. Technology"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              disabled={loading}
            />
          </FormGroup>

          <FormGroup label="Country">
            <input 
              type="text" 
              className="formInput"
              placeholder="e.g. US"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              disabled={loading}
            />
          </FormGroup>

          <FormGroup label="Company Logo">
            <input 
              type="file" 
              accept="image/*"
              className="fileInput"
              onChange={handleFileChange}
              disabled={loading}
            />
            {logoPreview && (
              <div>
                <img src={logoPreview} alt="Preview" className="logoPreview" />
              </div>
            )}
          </FormGroup>
        </ModalBody>

        <ModalFooter>
          <button type="button" className="cancelBtn" onClick={() => onClose(false)} disabled={loading}>
            Cancel
          </button>
          <button type="submit" className="saveBtn" disabled={loading}>
            {loading ? 'Saving...' : 'Save Company'}
          </button>
        </ModalFooter>
      </form>
    </Modal>
  );
}
