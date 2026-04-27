import { useEffect, useMemo, useRef, useState } from 'react';
import './ProfilePage.css';
import { useNavigate } from 'react-router-dom';
import Select from 'react-select';
import NaicsMultiSelect from '../components/NaicsMultiSelect';
import useNotificationSummary from '../hooks/useNotificationSummary';

const ACCEPTED_DOCUMENT_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg'];
const ACCEPTED_DOCUMENT_MIME_TYPES = ['application/pdf', 'image/png', 'image/jpeg'];
const GMAIL_AUTH_API_URL = 'http://127.0.0.1:8000/accounts/gmail/auth/';
const CONNECTED_ACCOUNTS_API_URL = 'http://127.0.0.1:8000/accounts/connected-accounts/';
const SERVICES_OFFERED_OPTIONS = [
  'Software Development',
  'Cybersecurity',
  'Data Analytics',
  'AI / Machine Learning',
  'Cloud Services',
  'IT Support',
  'Workforce Training',
  'Manufacturing Support',
  'Grant Writing',
  'Project Management',
  'Business Consulting',
  'Engineering Services',
  'Robotics / Automation',
];
const TARGET_INDUSTRY_OPTIONS = [
  'Government',
  'Manufacturing',
  'Education',
  'Healthcare',
  'Defense',
  'Transportation',
  'Energy',
  'Construction',
  'Nonprofit',
  'Workforce Development',
  'Technology',
  'Public Safety',
];
const OPPORTUNITY_TYPE_OPTIONS = [
  'Prime Contract',
  'Subcontract',
  'Partnership',
  'Grant',
  'Training Contract',
  'Technical Services',
  'Consulting Contract',
  'Research Opportunity',
];
const MATCHMAKING_TAG_OPTIONS = [
  'Cybersecurity',
  'Application Development',
  'Data Dashboards',
  'Automation',
  'Cloud Migration',
  'AI',
  'Machine Learning',
  'Curriculum Development',
  'STEM Education',
  'Digital Transformation',
  'Compliance',
  'Database Management',
  'Technical Writing',
  'Procurement Support',
];
const GEOGRAPHIC_PREFERENCE_OPTIONS = [
  'Georgia',
  'Southeast',
  'Nationwide',
  'Remote',
  'Local Only',
  'Hybrid / On-site',
];
const MATCHMAKING_DETAIL_WARNING = 'Your profile is missing matchmaking details. Leaving Services Offered, Target Industries, Opportunity Types, Tags, or Geographic Preferences blank may lower your AI match percentages because the system has less information to compare against contracts.';

const defaultMailboxConnections = [
  {
    id: 'default-gmail',
    provider: 'Gmail',
    email: 'contracts@pinkstem.org',
    status: 'Connected',
    lastSynced: 'Not synced yet',
  },
  {
    id: 'default-outlook',
    provider: 'Outlook',
    email: 'opportunities@pinkstem.org',
    status: 'Needs attention',
    lastSynced: 'Not synced yet',
  },
];

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

function isSupportedDocument(file) {
  if (!file) {
    return false;
  }

  return isAcceptedDocument(file);
}

function inferMailboxProvider(email) {
  const normalizedEmail = String(email || '').toLowerCase();
  return normalizedEmail.includes('outlook') || normalizedEmail.includes('hotmail') || normalizedEmail.includes('live.')
    ? 'Outlook'
    : 'Gmail';
}

function formatMailboxSyncTime() {
  return new Date().toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function formatMailboxLastSynced(value) {
  if (!value) {
    return 'Not synced yet';
  }

  return new Date(value).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function toSelectOptions(values) {
  return values.map((value) => ({ value, label: value }));
}

function MatchmakingMultiSelect({ label, helperText, options, value, onChange }) {
  const selectOptions = useMemo(() => toSelectOptions(options), [options]);

  return (
    <div className="profile-field profile-field-full">
      <label className="profile-label">{label}</label>
      <p className="profile-field-helper">{helperText}</p>
      <Select
        isMulti
        isSearchable
        classNamePrefix="profile-match-select"
        options={selectOptions}
        value={selectOptions.filter((option) => value.includes(option.value))}
        onChange={(selected) => onChange(selected ? selected.map((option) => option.value) : [])}
      />
    </div>
  );
}

function ProfilePage() {
  const navigate = useNavigate();
  const [companyName, setCompanyName] = useState('');
  const [capabilitySummary, setCapabilitySummary] = useState('');
  const [coreCompetencies, setCoreCompetencies] = useState('');
  const [differentiators, setDifferentiators] = useState('');
  const [naicsCodes, setNaicsCodes] = useState([]);
  const [certifications, setCertifications] = useState('');
  const [pastPerformance, setPastPerformance] = useState('');
  const [servicesOffered, setServicesOffered] = useState([]);
  const [targetIndustries, setTargetIndustries] = useState([]);
  const [preferredOpportunityTypes, setPreferredOpportunityTypes] = useState([]);
  const [matchmakingTags, setMatchmakingTags] = useState([]);
  const [geographicPreferences, setGeographicPreferences] = useState([]);
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
  const [syncingMailboxIds, setSyncingMailboxIds] = useState([]);
  const [isSyncingAllMailboxes, setIsSyncingAllMailboxes] = useState(false);
  const linkedEmailsSectionRef = useRef(null);
  const [linkedEmails, setLinkedEmails] = useState([]);
  const [linkedEmailInput, setLinkedEmailInput] = useState('');
  const [linkedEmailLabel, setLinkedEmailLabel] = useState('');
  const [isSavingLinkedEmail, setIsSavingLinkedEmail] = useState(false);
  const [removingLinkedEmailId, setRemovingLinkedEmailId] = useState(null);
  const [showMatchmakingWarning, setShowMatchmakingWarning] = useState(false);

  const token = localStorage.getItem('token');
  const unreadCount = useNotificationSummary();

  const mailboxRows = useMemo(() => {
    const dynamicMailboxRows = linkedEmails.map((linkedEmail) => ({
      id: `linked-${linkedEmail.id}`,
      provider: inferMailboxProvider(linkedEmail.email),
      email: linkedEmail.email,
      status: 'Needs attention',
      lastSynced: 'Not synced yet',
    }));

    const rowMap = new Map();
    [...dynamicMailboxRows, ...mailboxConnections].forEach((row) => {
      rowMap.set(row.email, row);
    });

    return Array.from(rowMap.values());
  }, [linkedEmails, mailboxConnections]);

  const structuredData = {
    company_name: companyName,
    capability_summary: capabilitySummary,
    core_competencies: coreCompetencies,
    differentiators: differentiators,
    naics_codes: naicsCodes,
    certifications: certifications,
    past_performance: pastPerformance,
    services_offered: servicesOffered,
    target_industries: targetIndustries,
    preferred_opportunity_types: preferredOpportunityTypes,
    matchmaking_tags: matchmakingTags,
    geographic_preferences: geographicPreferences,
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
    setServicesOffered(Array.isArray(profile.services_offered) ? profile.services_offered : []);
    setTargetIndustries(Array.isArray(profile.target_industries) ? profile.target_industries : []);
    setPreferredOpportunityTypes(Array.isArray(profile.preferred_opportunity_types) ? profile.preferred_opportunity_types : []);
    setMatchmakingTags(Array.isArray(profile.matchmaking_tags) ? profile.matchmaking_tags : []);
    setGeographicPreferences(Array.isArray(profile.geographic_preferences) ? profile.geographic_preferences : []);
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
        const [profileResponse, linkedEmailsResponse, connectedAccountsResponse] = await Promise.all([
          fetch('http://127.0.0.1:8000/api/profile/', {
            method: 'GET',
            headers,
          }),
          fetch('http://127.0.0.1:8000/accounts/linked-emails/', {
            method: 'GET',
            headers,
          }),
          fetch(CONNECTED_ACCOUNTS_API_URL, {
            method: 'GET',
            headers,
          }),
        ]);

        const profileData = await profileResponse.json();
        const linkedEmailsData = await linkedEmailsResponse.json();
        const connectedAccountsData = await connectedAccountsResponse.json();

        if (!profileResponse.ok) {
          setUploadError(profileData.message || 'Failed to load profile.');
          return;
        }

        if (!linkedEmailsResponse.ok) {
          setUploadError(linkedEmailsData.error || 'Failed to load linked emails.');
          return;
        }

        if (!connectedAccountsResponse.ok) {
          setUploadError(connectedAccountsData.error || 'Failed to load mailbox connections.');
          return;
        }

        fillProfileFields(profileData.profile || profileData || {});
        setEditing(Boolean(profileData.editing));
        setLastProcessedFile(profileData.processed_file_name || 'None');
        setLinkedEmails(linkedEmailsData.emails || []);
        setMailboxConnections((connectedAccountsData.mailboxes || []).map((mailbox) => ({
          id: `connected-${mailbox.id}`,
          accountId: mailbox.id,
          provider: mailbox.provider === 'gmail' ? 'Gmail' : 'Outlook',
          email: mailbox.email,
          status: mailbox.status || (mailbox.is_active ? 'Connected' : 'Needs attention'),
          lastSynced: formatMailboxLastSynced(mailbox.last_synced_at),
        })));
      } catch {
        setUploadError('Could not load saved profile.');
      }
    };

    loadProfile();
  }, [token]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];

    if (file && !isAcceptedDocument(file)) {
      setSelectedFile(null);
      setUploadError('Please upload a PDF, PNG, JPG, or JPEG file.');
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
      setUploadError('Please choose a PDF, PNG, JPG, or JPEG file first.');
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
    } catch {
      setUploadError('Could not connect to the server.');
    } finally {
      setIsUploading(false);
    }
  };

  const countEmptyMatchmakingFields = () => [
    servicesOffered,
    targetIndustries,
    preferredOpportunityTypes,
    matchmakingTags,
    geographicPreferences,
  ].filter((values) => !Array.isArray(values) || values.length === 0).length;

  const saveProfile = async () => {
    setIsSaving(true);
    setUploadError('');
    setSuccessMessage('');
    setShowMatchmakingWarning(false);

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
    } catch {
      setUploadError('Could not connect to the server.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveProfile = () => {
    if (countEmptyMatchmakingFields() >= 2) {
      setShowMatchmakingWarning(true);
      return;
    }

    saveProfile();
  };

  const handleConnectMailbox = async (email, provider) => {
    if (provider === 'Gmail') {
      if (!token) {
        setUploadError('Please log in before connecting Gmail.');
        return;
      }

      try {
        const response = await fetch(GMAIL_AUTH_API_URL, {
          headers: {
            Authorization: `Token ${token}`,
          },
        });
        const data = await response.json();

        if (!response.ok) {
          setUploadError(data.error || 'Failed to start Gmail authorization.');
          return;
        }

        window.location.href = data.auth_url;
      } catch {
        setUploadError('Could not connect to the server.');
      }
      return;
    }

    setMailboxConnections((currentConnections) => {
      const existingConnection = currentConnections.find((connection) => connection.email === email);

      if (existingConnection) {
        return currentConnections.map((connection) => (
          connection.email === email
            ? { ...connection, provider, status: 'Connected' }
            : connection
        ));
      }

      return [
        ...currentConnections,
        {
          id: `mailbox-${Date.now()}`,
          provider,
          email,
          status: 'Connected',
          lastSynced: 'Not synced yet',
        },
      ];
    });

    setSuccessMessage(`${provider} mailbox connected for ${email}.`);
    setUploadError('');
  };

  const updateSyncedMailboxRows = (mailboxes) => {
    setMailboxConnections((currentConnections) => currentConnections.map((connection) => {
      const syncedMailbox = mailboxes.find((mailbox) => mailbox.id === connection.accountId);
      if (!syncedMailbox) {
        return connection;
      }

      return {
        ...connection,
        lastSynced: formatMailboxLastSynced(syncedMailbox.last_synced_at),
        status: 'Connected',
      };
    }));
  };

  const handleSyncMailbox = async (mailbox) => {
    if (!mailbox.accountId) {
      setUploadError('Connect this mailbox before syncing.');
      return;
    }

    setSyncingMailboxIds((currentIds) => [...currentIds, mailbox.accountId]);
    setUploadError('');

    try {
      const response = await fetch(`${CONNECTED_ACCOUNTS_API_URL}${mailbox.accountId}/sync/`, {
        method: 'POST',
        headers: {
          Authorization: `Token ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ limit: 25 }),
      });
      const data = await response.json();

      if (!response.ok || !data.success) {
        setUploadError(data.error || 'Mailbox sync failed.');
        return;
      }

      updateSyncedMailboxRows([data.mailbox]);
      setSuccessMessage(`Mailbox sync completed for ${mailbox.email}.`);
    } catch {
      setUploadError('Could not connect to the server.');
    } finally {
      setSyncingMailboxIds((currentIds) => currentIds.filter((id) => id !== mailbox.accountId));
    }
  };

  const handleSyncAllMailboxes = async () => {
    setIsSyncingAllMailboxes(true);
    setUploadError('');

    try {
      const response = await fetch(`${CONNECTED_ACCOUNTS_API_URL}sync-all/`, {
        method: 'POST',
        headers: {
          Authorization: `Token ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ limit: 25 }),
      });
      const data = await response.json();

      if (!response.ok) {
        setUploadError(data.error || 'Mailbox sync failed.');
        return;
      }

      updateSyncedMailboxRows(data.mailboxes || []);
      if (data.success) {
        setSuccessMessage(`Synced ${data.synced_count} mailbox${data.synced_count === 1 ? '' : 'es'}.`);
      } else {
        setUploadError(`Synced ${data.synced_count} mailbox${data.synced_count === 1 ? '' : 'es'}; ${data.failed_count} failed.`);
      }
    } catch {
      setUploadError('Could not connect to the server.');
    } finally {
      setIsSyncingAllMailboxes(false);
    }
  };

  const scrollToLinkedEmails = () => {
    linkedEmailsSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    } catch {
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
    } catch {
      setUploadError('Could not connect to the server.');
    } finally {
      setRemovingLinkedEmailId(null);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
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
            <div className="profile-page-heading-row">
              <div>
                <h1 className="profile-page-title">Profile</h1>
                <p className="profile-subtitle">
                  Enter your profile manually anytime, and optionally use document extraction to pre-fill fields.
                </p>
              </div>
              <button
                className="profile-light-button profile-logout-button"
                type="button"
                onClick={handleLogout}
              >
                Log Out
              </button>
            </div>

            {uploadError && <p className="profile-error-message">{uploadError}</p>}
            {successMessage && <p className="profile-success-message">{successMessage}</p>}
            {editing && <p className="profile-editing-message">Editing existing capability profile</p>}

            <section className="profile-section-card">
              <div className="profile-section-heading-row">
                <div>
                  <h2 className="profile-section-title">Mailbox Connections</h2>
                  <p className="profile-section-description">
                    Connect Gmail or Outlook mailboxes to pull in opportunity emails and manage connection and sync status beside each email.
                  </p>
                </div>
                <div className="mailbox-actions-row">
                  <button
                    className="profile-light-button"
                    type="button"
                    onClick={scrollToLinkedEmails}
                  >
                    Add Email
                  </button>
                  <button
                    className="profile-dark-button"
                    type="button"
                    onClick={handleSyncAllMailboxes}
                    disabled={isSyncingAllMailboxes}
                  >
                    {isSyncingAllMailboxes ? 'Syncing...' : 'Sync All'}
                  </button>
                </div>
              </div>

              <div className="mailbox-list">
                {mailboxRows.map((mailbox) => (
                  <div key={mailbox.id} className="mailbox-card mailbox-card-with-actions">
                    <div>
                      <h3 className="mailbox-provider">{mailbox.provider}</h3>
                      <p className="mailbox-email">{mailbox.email}</p>
                      <p className="mailbox-sync-meta">Last synced: {mailbox.lastSynced || 'Not synced yet'}</p>
                    </div>
                    <div className="mailbox-actions-column">
                      <div className="mailbox-actions-row">
                        <button
                          className="profile-light-button mailbox-action-button"
                          type="button"
                          onClick={() => handleConnectMailbox(mailbox.email, mailbox.provider)}
                        >
                          Connect
                        </button>
                        <button
                          className="profile-dark-button mailbox-action-button"
                          type="button"
                          onClick={() => handleSyncMailbox(mailbox)}
                          disabled={!mailbox.accountId || syncingMailboxIds.includes(mailbox.accountId)}
                        >
                          {syncingMailboxIds.includes(mailbox.accountId) ? 'Syncing...' : 'Sync'}
                        </button>
                      </div>
                      <span className={`mailbox-status ${mailbox.status === 'Connected' ? 'mailbox-status-connected' : 'mailbox-status-warning'}`}>
                        {mailbox.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="profile-section-card" ref={linkedEmailsSectionRef}>
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
              <h2 className="profile-section-title">Company Information</h2>
              <div className="profile-form-grid">
                <div className="profile-field">
                  <label className="profile-label">Company Name</label>
                  <input className="profile-input" value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
                </div>
                <div className="profile-field">
                  <label className="profile-label">Website</label>
                  <input className="profile-input" value={website} onChange={(e) => setWebsite(e.target.value)} />
                </div>
                <div className="profile-field">
                  <label className="profile-label">Contact Name</label>
                  <input className="profile-input" value={contactName} onChange={(e) => setContactName(e.target.value)} />
                </div>
                <div className="profile-field">
                  <label className="profile-label">Contact Email</label>
                  <input className="profile-input" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
                </div>
                <div className="profile-field">
                  <label className="profile-label">Contact Phone</label>
                  <input className="profile-input" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} />
                </div>
                <div className="profile-field profile-field-full">
                  <label className="profile-label">Capability Summary</label>
                  <textarea className="profile-textarea" rows="4" value={capabilitySummary} onChange={(e) => setCapabilitySummary(e.target.value)} />
                </div>
                <div className="profile-field profile-field-full">
                  <label className="profile-label">Core Competencies</label>
                  <textarea className="profile-textarea" rows="4" value={coreCompetencies} onChange={(e) => setCoreCompetencies(e.target.value)} />
                </div>
                <div className="profile-field profile-field-full">
                  <label className="profile-label">Differentiators</label>
                  <textarea className="profile-textarea" rows="4" value={differentiators} onChange={(e) => setDifferentiators(e.target.value)} />
                </div>
                <div className="profile-field profile-field-full">
                  <label className="profile-label">NAICS Codes</label>
                  <NaicsMultiSelect value={naicsCodes} onChange={setNaicsCodes} />
                </div>
                <div className="profile-field profile-field-full">
                  <label className="profile-label">Certifications</label>
                  <textarea className="profile-textarea" rows="3" value={certifications} onChange={(e) => setCertifications(e.target.value)} />
                </div>
                <div className="profile-field profile-field-full">
                  <label className="profile-label">Past Performance</label>
                  <textarea className="profile-textarea" rows="4" value={pastPerformance} onChange={(e) => setPastPerformance(e.target.value)} />
                </div>
              </div>
            </section>

            <section className="profile-section-card">
              <h2 className="profile-section-title">Matchmaking Preferences</h2>
              <p className="profile-section-description">
                These structured selections improve AI match percentages by giving the system cleaner signals to compare against contracts.
              </p>
              <div className="profile-form-grid">
                <MatchmakingMultiSelect
                  label="Services Offered"
                  helperText="Select the main services your organization can deliver."
                  options={SERVICES_OFFERED_OPTIONS}
                  value={servicesOffered}
                  onChange={setServicesOffered}
                />
                <MatchmakingMultiSelect
                  label="Target Industries"
                  helperText="Select the sectors where your work is strongest."
                  options={TARGET_INDUSTRY_OPTIONS}
                  value={targetIndustries}
                  onChange={setTargetIndustries}
                />
                <MatchmakingMultiSelect
                  label="Preferred Opportunity Types"
                  helperText="Select the contract or funding formats you want prioritized."
                  options={OPPORTUNITY_TYPE_OPTIONS}
                  value={preferredOpportunityTypes}
                  onChange={setPreferredOpportunityTypes}
                />
                <MatchmakingMultiSelect
                  label="Matchmaking Tags"
                  helperText="Select specific keywords that describe high-fit work."
                  options={MATCHMAKING_TAG_OPTIONS}
                  value={matchmakingTags}
                  onChange={setMatchmakingTags}
                />
                <MatchmakingMultiSelect
                  label="Geographic Preferences"
                  helperText="Select locations or delivery modes that fit your team."
                  options={GEOGRAPHIC_PREFERENCE_OPTIONS}
                  value={geographicPreferences}
                  onChange={setGeographicPreferences}
                />
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
            <h3 className="profile-modal-title">Upload Capability Document</h3>
            <div className="profile-modal-body">
              <input type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" onChange={handleFileChange} />
              {selectedFile && (
                <p className="profile-modal-file-name">
                  Selected: {selectedFile.name}
                  {!isSupportedDocument(selectedFile) && ' (unsupported file type)'}
                </p>
              )}
            </div>
            <div className="profile-modal-actions">
              <button className="profile-light-button" type="button" onClick={() => setShowUploadModal(false)}>
                Cancel
              </button>
              <button className="profile-dark-button" type="button" onClick={handleExtractPrefill} disabled={isUploading}>
                {isUploading ? 'Processing...' : 'Extract and Prefill'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showMatchmakingWarning && (
        <div className="profile-modal-overlay">
          <div className="profile-modal profile-warning-modal">
            <h3 className="profile-modal-title">Complete Matchmaking Details</h3>
            <p className="profile-modal-warning-text">{MATCHMAKING_DETAIL_WARNING}</p>
            <div className="profile-modal-actions">
              <button className="profile-light-button" type="button" onClick={() => setShowMatchmakingWarning(false)}>
                Go Back and Complete Profile
              </button>
              <button className="profile-dark-button" type="button" onClick={saveProfile} disabled={isSaving}>
                {isSaving ? 'Saving...' : 'Save Anyway'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfilePage;
