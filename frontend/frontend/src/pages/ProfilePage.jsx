import { useEffect, useMemo, useState } from 'react';
import './ProfilePage.css';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const EMPTY_PROFILE = {
  company_name: '',
  capability_summary: '',
  core_competencies: '',
  differentiators: '',
  naics_codes: '',
  certifications: '',
  past_performance: '',
  contact_name: '',
  contact_email: '',
  contact_phone: '',
  website: '',
};

function ProfilePage() {
  const navigate = useNavigate();
  const [companyName, setCompanyName] = useState('');
  const [capabilitySummary, setCapabilitySummary] = useState('');
  const [coreCompetencies, setCoreCompetencies] = useState('');
  const [differentiators, setDifferentiators] = useState('');
  const [naicsCodes, setNaicsCodes] = useState('');
  const [certifications, setCertifications] = useState('');
  const [pastPerformance, setPastPerformance] = useState('');
  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [website, setWebsite] = useState('');

  const [selectedFile, setSelectedFile] = useState(null);
  const [lastProcessedFile, setLastProcessedFile] = useState('None');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [editing, setEditing] = useState(false);
  const [extractedText, setExtractedText] = useState('');

  const [mailboxConnections, setMailboxConnections] = useState([]);
  const [mailboxStates, setMailboxStates] = useState({});
  const [isLoadingMailboxes, setIsLoadingMailboxes] = useState(true);
  const [showAddEmailForm, setShowAddEmailForm] = useState(false);
  const [newMailboxEmail, setNewMailboxEmail] = useState('');
  const [newMailboxLabel, setNewMailboxLabel] = useState('');
  const [isAddingMailbox, setIsAddingMailbox] = useState(false);

  const token = localStorage.getItem('token');

  const structuredData = {
    company_name: companyName,
    capability_summary: capabilitySummary,
    core_competencies: coreCompetencies,
    differentiators: differentiators,
    naics_codes: naicsCodes,
    certifications: certifications,
    past_performance: pastPerformance,
    contact_name: contactName,
    contact_email: contactEmail,
    contact_phone: contactPhone,
    website: website,
  };

  const fillProfileFields = (profile = EMPTY_PROFILE) => {
    setCompanyName(profile.company_name || '');
    setCapabilitySummary(profile.capability_summary || '');
    setCoreCompetencies(profile.core_competencies || '');
    setDifferentiators(profile.differentiators || '');
    setNaicsCodes(profile.naics_codes || '');
    setCertifications(profile.certifications || '');
    setPastPerformance(profile.past_performance || '');
    setContactName(profile.contact_name || '');
    setContactEmail(profile.contact_email || '');
    setContactPhone(profile.contact_phone || '');
    setWebsite(profile.website || '');
  };

  const getMailboxProvider = (email) => {
    const normalizedEmail = (email || '').toLowerCase();

    if (normalizedEmail.includes('gmail.com')) {
      return 'Gmail';
    }

    if (
      normalizedEmail.includes('outlook.com') ||
      normalizedEmail.includes('hotmail.com') ||
      normalizedEmail.includes('live.com')
    ) {
      return 'Outlook';
    }

    return 'Email';
  };

  const displayedMailboxes = useMemo(() => {
    return mailboxConnections.map((mailbox) => {
      const mailboxState = mailboxStates[mailbox.id] || {};
      return {
        ...mailbox,
        provider: getMailboxProvider(mailbox.email),
        connectedProvider: mailboxState.connectedProvider || '',
        status: mailboxState.status || 'Not connected',
      };
    });
  }, [mailboxConnections, mailboxStates]);

  const parseJsonResponse = async (response) => {
    const text = await response.text();
    return text ? JSON.parse(text) : {};
  };

  const authorizedHeaders = (includeJson = false) => {
    const headers = {};

    if (token) {
      headers.Authorization = `Token ${token}`;
    }

    if (includeJson) {
      headers['Content-Type'] = 'application/json';
    }

    return headers;
  };

  const clearMessages = () => {
    setUploadError('');
    setSuccessMessage('');
  };

  const loadLinkedEmails = async () => {
    if (!token) {
      setIsLoadingMailboxes(false);
      return;
    }

    setIsLoadingMailboxes(true);

    try {
      const response = await fetch(`${API_BASE_URL}/accounts/linked-emails/`, {
        method: 'GET',
        headers: authorizedHeaders(),
      });

      const data = await parseJsonResponse(response);

      if (!response.ok) {
        setUploadError(data.error || 'Failed to load linked emails.');
        return;
      }

      setMailboxConnections(Array.isArray(data.emails) ? data.emails : []);
    } catch (error) {
      setUploadError('Could not load linked emails.');
    } finally {
      setIsLoadingMailboxes(false);
    }
  };

  useEffect(() => {
    const loadProfile = async () => {
      if (!token) return;

      try {
        const response = await fetch(`${API_BASE_URL}/api/profile/`, {
          method: 'GET',
          headers: authorizedHeaders(),
        });

        const data = await parseJsonResponse(response);

        if (!response.ok) {
          setUploadError(data.message || 'Failed to load profile.');
          return;
        }

        fillProfileFields(data.profile || data || EMPTY_PROFILE);
        setEditing(Boolean(data.editing));
        setLastProcessedFile(data.processed_file_name || 'None');
      } catch (error) {
        setUploadError('Could not load saved profile.');
      }
    };

    loadProfile();
    loadLinkedEmails();
  }, [token]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setSelectedFile(file || null);
    clearMessages();
  };

  const handleExtractPrefill = async () => {
    if (!selectedFile) {
      setUploadError('Please choose a PDF first.');
      return;
    }

    const formData = new FormData();
    formData.append('capability_pdf', selectedFile);

    setIsUploading(true);
    clearMessages();

    try {
      const response = await fetch(`${API_BASE_URL}/api/profile/extract/`, {
        method: 'POST',
        headers: authorizedHeaders(),
        body: formData,
      });

      const data = await parseJsonResponse(response);

      if (!response.ok) {
        setUploadError(data.message || 'Failed to process PDF.');
        return;
      }

      fillProfileFields(data.profile || data || EMPTY_PROFILE);
      setLastProcessedFile(data.processed_file_name || 'None');
      setExtractedText(data.extracted_text || '');
      setSuccessMessage(data.message || 'Fields extracted successfully.');
      setShowUploadModal(false);
    } catch (error) {
      setUploadError('Could not connect to the server.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    clearMessages();

    try {
      const response = await fetch(`${API_BASE_URL}/api/profile/save/`, {
        method: 'POST',
        headers: authorizedHeaders(true),
        body: JSON.stringify(structuredData),
      });

      const data = await parseJsonResponse(response);

      if (!response.ok) {
        setUploadError(data.message || 'Failed to save profile.');
        return;
      }

      setSuccessMessage(data.message || 'Capability profile saved successfully.');
      setEditing(true);
    } catch (error) {
      setUploadError('Could not connect to the server.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddEmail = async () => {
    if (!newMailboxEmail.trim()) {
      setUploadError('Please enter an email address.');
      return;
    }

    setIsAddingMailbox(true);
    clearMessages();

    try {
      const response = await fetch(`${API_BASE_URL}/accounts/linked-emails/`, {
        method: 'POST',
        headers: authorizedHeaders(true),
        body: JSON.stringify({
          email: newMailboxEmail,
          label: newMailboxLabel,
        }),
      });

      const data = await parseJsonResponse(response);

      if (!response.ok) {
        setUploadError(data.error || 'Failed to add email.');
        return;
      }

      setMailboxConnections((currentConnections) => [
        ...currentConnections,
        data.email,
      ]);
      setNewMailboxEmail('');
      setNewMailboxLabel('');
      setShowAddEmailForm(false);
      setSuccessMessage(data.message || 'Email added successfully.');
    } catch (error) {
      setUploadError('Could not connect to the server.');
    } finally {
      setIsAddingMailbox(false);
    }
  };

  const handleConnectMailbox = (mailboxId, provider) => {
    setMailboxStates((currentStates) => ({
      ...currentStates,
      [mailboxId]: {
        connectedProvider: provider,
        status: 'Connected',
      },
    }));

    setSuccessMessage(`${provider} connected for this mailbox.`);
    setUploadError('');
  };

  return (
    <div className="profile-layout">
      <aside className="profile-sidebar">
        <h2 className="profile-sidebar-title">AI Matchmaking Tool</h2>

        <nav className="profile-sidebar-nav">
          <button className="profile-sidebar-link" onClick={() => navigate('/dashboard')}>
            Dashboard
          </button>
          <button className="profile-sidebar-link" onClick={() => navigate('/dashboard')}>
            AI Matchmaking
          </button>
          <button className="profile-sidebar-link active" onClick={() => navigate('/profile')}>
            Profile
          </button>
          <button className="profile-sidebar-link" onClick={() => navigate('/notifications')}>
            Notifications
          </button>
        </nav>
      </aside>

      <div className="profile-main">
        <header className="profile-topbar">
          <div className="profile-inner">
            <input
              type="text"
              placeholder="Search contracts..."
              className="profile-search-bar"
            />
            <div className="profile-topbar-icons">
              <span
                className="profile-icon-circle"
                onClick={() => navigate('/notifications')}
                style={{ cursor: 'pointer' }}
                title="Notifications"
              >
                3
              </span>

              <span
                className="profile-icon-placeholder"
                onClick={() => navigate('/profile')}
                style={{ cursor: 'pointer' }}
                title="Profile"
              >
                👤
              </span>
            </div>
          </div>
        </header>

        <main className="profile-content">
          <div className="profile-inner">
            <h1 className="profile-page-title">Profile</h1>
            <p className="profile-subtitle">
              Enter your profile manually anytime, and optionally use PDF OCR to pre-fill fields.
            </p>

            {uploadError && <p className="profile-error-message">{uploadError}</p>}
            {successMessage && <p className="profile-success-message">{successMessage}</p>}
            {editing && <p className="profile-editing-message">Editing existing capability profile</p>}

            <section className="profile-section-card">
              <div className="mailbox-header-row">
                <div>
                  <h2 className="profile-section-title">Mailbox Connections</h2>
                  <p className="profile-section-description">
                    Add multiple email accounts, then choose Gmail or Outlook for each mailbox connection.
                  </p>
                </div>

                <button
                  className="profile-dark-button"
                  onClick={() => setShowAddEmailForm((currentValue) => !currentValue)}
                >
                  {showAddEmailForm ? 'Cancel' : 'Add Email'}
                </button>
              </div>

              {showAddEmailForm && (
                <div className="mailbox-add-panel">
                  <div className="mailbox-add-grid">
                    <div className="profile-field">
                      <label className="profile-label">Email address</label>
                      <input
                        type="email"
                        value={newMailboxEmail}
                        onChange={(e) => setNewMailboxEmail(e.target.value)}
                        className="profile-input"
                        placeholder="name@company.com"
                      />
                    </div>

                    <div className="profile-field">
                      <label className="profile-label">Label</label>
                      <input
                        type="text"
                        value={newMailboxLabel}
                        onChange={(e) => setNewMailboxLabel(e.target.value)}
                        className="profile-input"
                        placeholder="Contracts inbox"
                      />
                    </div>
                  </div>

                  <div className="mailbox-add-actions">
                    <button
                      className="profile-dark-button"
                      onClick={handleAddEmail}
                      disabled={isAddingMailbox}
                    >
                      {isAddingMailbox ? 'Adding...' : 'Save Email'}
                    </button>
                  </div>
                </div>
              )}

              <div className="mailbox-list">
                {isLoadingMailboxes ? (
                  <div className="mailbox-card">
                    <p className="mailbox-empty-text">Loading mailboxes...</p>
                  </div>
                ) : displayedMailboxes.length === 0 ? (
                  <div className="mailbox-card">
                    <p className="mailbox-empty-text">No additional emails yet. Add one to connect a mailbox.</p>
                  </div>
                ) : (
                  displayedMailboxes.map((mailbox) => (
                    <div key={mailbox.id} className="mailbox-card mailbox-card-with-actions">
                      <div className="mailbox-info-block">
                        <div className="mailbox-title-row">
                          <h3 className="mailbox-provider">{mailbox.label || mailbox.provider}</h3>
                          <span className={`mailbox-status ${mailbox.status === 'Connected' ? 'mailbox-status-connected' : 'mailbox-status-warning'}`}>
                            {mailbox.status}
                          </span>
                        </div>
                        <p className="mailbox-email">{mailbox.email}</p>
                        <p className="mailbox-provider-caption">
                          Detected provider: {mailbox.provider}
                          {mailbox.connectedProvider ? ` • Connected via ${mailbox.connectedProvider}` : ''}
                        </p>
                      </div>

                      <div className="mailbox-action-group">
                        <button
                          className="profile-dark-button mailbox-connect-button"
                          onClick={() => handleConnectMailbox(mailbox.id, 'Gmail')}
                        >
                          Connect Gmail
                        </button>
                        <button
                          className="profile-light-button mailbox-connect-button"
                          onClick={() => handleConnectMailbox(mailbox.id, 'Outlook')}
                        >
                          Connect Outlook
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="profile-section-card">
              <h2 className="profile-section-title">Capability Documents</h2>

              <div className="profile-button-row">
                <button
                  className="profile-dark-button"
                  onClick={() => setShowUploadModal(true)}
                >
                  Upload Capability Document
                </button>

                <button
                  className="profile-light-button"
                  onClick={handleSaveProfile}
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving...' : 'Save Profile'}
                </button>
              </div>

              <p className="profile-last-file">
                <strong>Last processed file:</strong> {lastProcessedFile}
              </p>
            </section>

            <section className="profile-section-card">
              <h2 className="profile-section-title">Capability Profile</h2>

              <div className="profile-form-grid">
                <div className="profile-field">
                  <label className="profile-label">Company name</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="profile-input"
                  />
                </div>

                <div className="profile-field profile-field-full">
                  <label className="profile-label">Capability summary</label>
                  <textarea
                    value={capabilitySummary}
                    onChange={(e) => setCapabilitySummary(e.target.value)}
                    className="profile-textarea"
                    rows="4"
                  />
                </div>

                <div className="profile-field profile-field-full">
                  <label className="profile-label">Core competencies</label>
                  <textarea
                    value={coreCompetencies}
                    onChange={(e) => setCoreCompetencies(e.target.value)}
                    className="profile-textarea"
                    rows="3"
                  />
                </div>

                <div className="profile-field profile-field-full">
                  <label className="profile-label">Differentiators</label>
                  <textarea
                    value={differentiators}
                    onChange={(e) => setDifferentiators(e.target.value)}
                    className="profile-textarea"
                    rows="3"
                  />
                </div>

                <div className="profile-field">
                  <label className="profile-label">NAICS codes</label>
                  <input
                    type="text"
                    value={naicsCodes}
                    onChange={(e) => setNaicsCodes(e.target.value)}
                    className="profile-input"
                  />
                </div>

                <div className="profile-field profile-field-full">
                  <label className="profile-label">Certifications</label>
                  <textarea
                    value={certifications}
                    onChange={(e) => setCertifications(e.target.value)}
                    className="profile-textarea"
                    rows="3"
                  />
                </div>

                <div className="profile-field profile-field-full">
                  <label className="profile-label">Past performance</label>
                  <textarea
                    value={pastPerformance}
                    onChange={(e) => setPastPerformance(e.target.value)}
                    className="profile-textarea"
                    rows="3"
                  />
                </div>
              </div>
            </section>

            <section className="profile-section-card">
              <h2 className="profile-section-title">Contact Information</h2>

              <div className="profile-form-grid">
                <div className="profile-field">
                  <label className="profile-label">Contact name</label>
                  <input
                    type="text"
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    className="profile-input"
                  />
                </div>

                <div className="profile-field">
                  <label className="profile-label">Contact email</label>
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    className="profile-input"
                  />
                </div>

                <div className="profile-field">
                  <label className="profile-label">Contact phone</label>
                  <input
                    type="text"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    className="profile-input"
                  />
                </div>

                <div className="profile-field">
                  <label className="profile-label">Website</label>
                  <input
                    type="text"
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                    className="profile-input"
                  />
                </div>
              </div>
            </section>

            {extractedText && (
              <section className="profile-section-card">
                <h2 className="profile-section-title">Extracted Text</h2>
                <pre className="profile-structured-data">{extractedText}</pre>
              </section>
            )}

            <section className="profile-section-card">
              <h2 className="profile-section-title">Structured Data (Dictionary View)</h2>
              <pre className="profile-structured-data">
                {JSON.stringify(structuredData, null, 2)}
              </pre>
            </section>
          </div>
        </main>
      </div>

      {showUploadModal && (
        <div className="profile-modal-overlay">
          <div className="profile-modal">
            <h2 className="profile-modal-title">Upload Capability Document</h2>

            <div className="profile-modal-body">
              <input type="file" accept=".pdf" onChange={handleFileChange} />
              <p className="profile-modal-file-name">
                {selectedFile ? selectedFile.name : 'No file selected'}
              </p>
            </div>

            <div className="profile-modal-actions">
              <button
                className="profile-dark-button"
                onClick={handleExtractPrefill}
                disabled={isUploading}
              >
                {isUploading ? 'Extracting...' : 'Extract + Prefill from PDF'}
              </button>
              <button
                className="profile-light-button"
                onClick={() => setShowUploadModal(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfilePage;
