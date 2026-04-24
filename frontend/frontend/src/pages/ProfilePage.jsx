import { useEffect, useState } from 'react';
import './ProfilePage.css';
import { useNavigate } from 'react-router-dom';
import NaicsMultiSelect from '../components/NaicsMultiSelect';
import useNotificationSummary from '../hooks/useNotificationSummary';

const ACCEPTED_DOCUMENT_EXTENSIONS = ['.pdf'];
const ACCEPTED_DOCUMENT_MIME_TYPES = ['application/pdf'];

function getFileExtension(filename) {
  const normalizedName = String(filename || '').toLowerCase();
  const extensionIndex = normalizedName.lastIndexOf('.');
  return extensionIndex >= 0 ? normalizedName.slice(extensionIndex) : '';
}

function isAcceptedDocument(file) {
  if (!file) {
    return false;
  }

  return (
    ACCEPTED_DOCUMENT_EXTENSIONS.includes(getFileExtension(file.name))
    || ACCEPTED_DOCUMENT_MIME_TYPES.includes(file.type)
  );
}

function isPdfDocument(file) {
  if (!file) {
    return false;
  }

  return getFileExtension(file.name) === '.pdf' || file.type === 'application/pdf';
}

const defaultMailboxConnections = [
  {
    id: 1,
    provider: 'Gmail',
    email: 'contracts@pinkstem.org',
    status: 'Connected',
  },
  {
    id: 2,
    provider: 'Outlook',
    email: 'opportunities@pinkstem.org',
    status: 'Needs attention',
  },
];

function ProfilePage() {
  const navigate = useNavigate();
  const [companyName, setCompanyName] = useState('');
  const [capabilitySummary, setCapabilitySummary] = useState('');
  const [coreCompetencies, setCoreCompetencies] = useState('');
  const [differentiators, setDifferentiators] = useState('');
  const [naicsCodes, setNaicsCodes] = useState([]);
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
  const [mailboxConnections, setMailboxConnections] = useState(defaultMailboxConnections);
  const [linkedEmails, setLinkedEmails] = useState([]);
  const [linkedEmailInput, setLinkedEmailInput] = useState('');
  const [linkedEmailLabel, setLinkedEmailLabel] = useState('');
  const [isSavingLinkedEmail, setIsSavingLinkedEmail] = useState(false);
  const [removingLinkedEmailId, setRemovingLinkedEmailId] = useState(null);

  const token = localStorage.getItem('token');
  const unreadCount = useNotificationSummary();

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

  const fillProfileFields = (profile) => {
    setCompanyName(profile.company_name || '');
    setCapabilitySummary(profile.capability_summary || '');
    setCoreCompetencies(profile.core_competencies || '');
    setDifferentiators(profile.differentiators || '');
    setNaicsCodes(profile.naics_codes || []);
    setCertifications(profile.certifications || '');
    setPastPerformance(profile.past_performance || '');
    setContactName(profile.contact_name || '');
    setContactEmail(profile.contact_email || '');
    setContactPhone(profile.contact_phone || '');
    setWebsite(profile.website || '');
  };

  useEffect(() => {
    const loadProfile = async () => {
      if (!token) return;

      try {
        const headers = {
          Authorization: `Token ${token}`,
        };
        const [profileResponse, linkedEmailsResponse] = await Promise.all([
          fetch('http://127.0.0.1:8000/api/profile/', {
            method: 'GET',
            headers,
          }),
          fetch('http://127.0.0.1:8000/accounts/linked-emails/', {
            method: 'GET',
            headers,
          }),
        ]);

        const profileData = await profileResponse.json();
        const linkedEmailsData = await linkedEmailsResponse.json();

        if (!profileResponse.ok) {
          setUploadError(profileData.message || 'Failed to load profile.');
          return;
        }

        if (!linkedEmailsResponse.ok) {
          setUploadError(linkedEmailsData.error || 'Failed to load linked emails.');
          return;
        }

        fillProfileFields(profileData.profile || profileData || {});
        setEditing(Boolean(profileData.editing));
        setLastProcessedFile(profileData.processed_file_name || 'None');
        setLinkedEmails(linkedEmailsData.emails || []);
      } catch (error) {
        setUploadError('Could not load saved profile.');
      }
    };

    loadProfile();
  }, [token]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];

    if (file && !isAcceptedDocument(file)) {
      setSelectedFile(null);
      setUploadError('Please upload a PDF file.');
      setSuccessMessage('');
      e.target.value = '';
      return;
    }

    setSelectedFile(file || null);
    setUploadError('');
    setSuccessMessage('');
  };

  const handleExtractPrefill = async () => {
    if (!selectedFile) {
      setUploadError('Please choose a PDF file first.');
      return;
    }

    const formData = new FormData();
    formData.append('capability_pdf', selectedFile);

    setIsUploading(true);
    setUploadError('');
    setSuccessMessage('');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/profile/extract/', {
        method: 'POST',
        headers: {
          Authorization: `Token ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setUploadError(data.message || 'Failed to process document.');
        setIsUploading(false);
        return;
      }

      fillProfileFields(data.profile || data || {});
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
    setUploadError('');
    setSuccessMessage('');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/profile/save/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Token ${token}`,
        },
        body: JSON.stringify(structuredData),
      });

      const data = await response.json();

      if (!response.ok) {
        setUploadError(data.message || 'Failed to save profile.');
        setIsSaving(false);
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

  const handleConnectMailbox = (provider) => {
    const defaultEmail = provider === 'Gmail'
      ? 'new.gmail.connection@example.com'
      : 'new.outlook.connection@example.com';

    setMailboxConnections((currentConnections) => {
      const existingConnection = currentConnections.find((connection) => connection.provider === provider);

      if (existingConnection) {
        return currentConnections.map((connection) => (
          connection.provider === provider
            ? { ...connection, status: 'Connected' }
            : connection
        ));
      }

      return [
        ...currentConnections,
        {
          id: Date.now(),
          provider,
          email: defaultEmail,
          status: 'Connected',
        },
      ];
    });

    setSuccessMessage(`${provider} mailbox connected.`);
    setUploadError('');
  };

  const handleAddLinkedEmail = async () => {
    if (!linkedEmailInput.trim()) {
      setUploadError('Enter an email address to add.');
      return;
    }

    setIsSavingLinkedEmail(true);
    setUploadError('');
    setSuccessMessage('');

    try {
      const response = await fetch('http://127.0.0.1:8000/accounts/linked-emails/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Token ${token}`,
        },
        body: JSON.stringify({
          email: linkedEmailInput,
          label: linkedEmailLabel,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setUploadError(data.error || 'Failed to add linked email.');
        return;
      }

      setLinkedEmails((currentEmails) => [...currentEmails, data.email]);
      setLinkedEmailInput('');
      setLinkedEmailLabel('');
      setSuccessMessage(data.message || 'Email added successfully.');
    } catch (error) {
      setUploadError('Could not connect to the server.');
    } finally {
      setIsSavingLinkedEmail(false);
    }
  };

  const handleRemoveLinkedEmail = async (emailId) => {
    setRemovingLinkedEmailId(emailId);
    setUploadError('');
    setSuccessMessage('');

    try {
      const response = await fetch(`http://127.0.0.1:8000/accounts/linked-emails/${emailId}/`, {
        method: 'DELETE',
        headers: {
          Authorization: `Token ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        setUploadError(data.error || 'Failed to remove linked email.');
        return;
      }

      setLinkedEmails((currentEmails) => currentEmails.filter((email) => email.id !== emailId));
      setSuccessMessage(data.message || 'Email removed successfully.');
    } catch (error) {
      setUploadError('Could not connect to the server.');
    } finally {
      setRemovingLinkedEmailId(null);
    }
  };

  return (
    <div className="profile-layout">
      <aside className="profile-sidebar">
        <h2 className="profile-sidebar-title">AI Matchmaking Tool</h2>

        <nav className="profile-sidebar-nav">
          <button className="profile-sidebar-link" onClick={() => navigate('/dashboard')}>
            Dashboard
          </button>
          <button className="profile-sidebar-link" onClick={() => navigate('/ai-matchmaking')}>
            AI Matchmaking
          </button>
          <button className="profile-sidebar-link" onClick={() => navigate('/my-contracts')}>
            My Contracts
          </button>
          <button className="profile-sidebar-link active" onClick={() => navigate('/profile')}>
            Profile
          </button>
          <button className="profile-sidebar-link" onClick={() => navigate('/notifications')}>
            <span className="profile-sidebar-link-content">
              <span>Notifications</span>
              {unreadCount > 0 && <span className="profile-nav-notification-badge">{unreadCount}</span>}
            </span>
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
              <h2 className="profile-section-title">Mailbox Connections</h2>
              <p className="profile-section-description">
                Connect Gmail or Outlook mailboxes to pull in opportunity emails and manage mailbox status.
              </p>

              <div className="profile-button-row">
                <button
                  className="profile-dark-button"
                  onClick={() => handleConnectMailbox('Gmail')}
                >
                  Connect Gmail
                </button>

                <button
                  className="profile-light-button"
                  onClick={() => handleConnectMailbox('Outlook')}
                >
                  Connect Outlook
                </button>
              </div>

              <div className="mailbox-list">
                {mailboxConnections.map((mailbox) => (
                  <div key={mailbox.id} className="mailbox-card">
                    <div>
                      <h3 className="mailbox-provider">{mailbox.provider}</h3>
                      <p className="mailbox-email">{mailbox.email}</p>
                    </div>
                    <span className={`mailbox-status ${mailbox.status === 'Connected' ? 'mailbox-status-connected' : 'mailbox-status-warning'}`}>
                      {mailbox.status}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <section className="profile-section-card">
              <h2 className="profile-section-title">Linked Emails</h2>
              <p className="profile-section-description">
                Add extra inboxes so opportunities can be compiled in one place for your account.
              </p>

              <div className="profile-linked-email-form">
                <input
                  type="email"
                  value={linkedEmailInput}
                  onChange={(e) => setLinkedEmailInput(e.target.value)}
                  className="profile-input"
                  placeholder="name@example.com"
                />
                <input
                  type="text"
                  value={linkedEmailLabel}
                  onChange={(e) => setLinkedEmailLabel(e.target.value)}
                  className="profile-input"
                  placeholder="Label (optional)"
                />
                <button
                  className="profile-dark-button"
                  onClick={handleAddLinkedEmail}
                  disabled={isSavingLinkedEmail}
                  type="button"
                >
                  {isSavingLinkedEmail ? 'Adding...' : 'Add Email'}
                </button>
              </div>

              <div className="linked-email-list">
                {linkedEmails.length === 0 ? (
                  <p className="linked-email-empty">No linked emails yet.</p>
                ) : (
                  linkedEmails.map((linkedEmail) => (
                    <div key={linkedEmail.id} className="linked-email-card">
                      <div>
                        <p className="linked-email-address">{linkedEmail.email}</p>
                        <p className="linked-email-label-text">{linkedEmail.label || 'No label'}</p>
                      </div>
                      <button
                        className="profile-light-button"
                        type="button"
                        onClick={() => handleRemoveLinkedEmail(linkedEmail.id)}
                        disabled={removingLinkedEmailId === linkedEmail.id}
                      >
                        {removingLinkedEmailId === linkedEmail.id ? 'Removing...' : 'Remove'}
                      </button>
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
                  {/* <label className="profile-label">NAICS codes</label> */}
                  <NaicsMultiSelect
                    value={naicsCodes}
                    onChange={setNaicsCodes}
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

            
          </div>
        </main>
      </div>

      {showUploadModal && (
        <div className="profile-modal-overlay">
          <div className="profile-modal">
            <h2 className="profile-modal-title">Upload Capability Document</h2>

            <div className="profile-modal-body">
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileChange}
              />
              <p className="profile-modal-file-name">
                {selectedFile ? selectedFile.name : 'No file selected'}
              </p>
              <p className="profile-modal-file-name">Accepted format: PDF</p>
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
