import { useEffect, useState } from 'react';
import './ProfilePage.css';
import { useNavigate } from 'react-router-dom';
import NaicsMultiSelect from '../components/NaicsMultiSelect';

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
        const response = await fetch('http://127.0.0.1:8000/api/profile/', {
          method: 'GET',
          headers: {
            Authorization: `Token ${token}`,
          },
        });

        const data = await response.json();

        if (!response.ok) {
          setUploadError(data.message || 'Failed to load profile.');
          return;
        }

        fillProfileFields(data.profile || data || {});
        setEditing(Boolean(data.editing));
        setLastProcessedFile(data.processed_file_name || 'None');
      } catch (error) {
        setUploadError('Could not load saved profile.');
      }
    };

    loadProfile();
  }, [token]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setSelectedFile(file || null);
    setUploadError('');
    setSuccessMessage('');
  };

  const handleExtractPrefill = async () => {
    if (!selectedFile) {
      setUploadError('Please choose a PDF first.');
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
        setUploadError(data.message || 'Failed to process PDF.');
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
