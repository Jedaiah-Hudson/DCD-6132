import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import './DashboardPage.css';
import './ContractDetailPage.css';

const API_BASE_URL = 'http://127.0.0.1:8000/api';
const PROGRESS_OPTIONS = [
  { value: 'NONE', label: 'Not tracked' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'WON', label: 'Won' },
  { value: 'LOST', label: 'Lost' },
];
const WORKFLOW_OPTIONS = [
  { value: 'NOT_STARTED', label: 'Not Started' },
  { value: 'REVIEWING', label: 'Reviewing' },
  { value: 'DRAFTING', label: 'Drafting' },
  { value: 'SUBMITTED', label: 'Submitted' },
];
const PROGRESS_STATUS_COLORS = {
  NONE: 'gray',
  PENDING: 'amber',
  WON: 'green',
  LOST: 'red',
};
const WORKFLOW_STATUS_COLORS = {
  NOT_STARTED: 'gray',
  REVIEWING: 'amber',
  DRAFTING: 'blue',
  SUBMITTED: 'green',
};
const LISTING_STATUS_COLORS = {
  active: 'green',
  inactive: 'gray',
  unknown: 'gray',
  yes: 'green',
  no: 'gray',
};
const NAICS_CATEGORY_COLORS = {
  construction: 'orange',
  manufacturing: 'indigo',
  transportation_logistics: 'teal',
  information: 'blue',
  software: 'violet',
  software_it: 'violet',
  it_services: 'violet',
  professional_services: 'purple',
  engineering: 'blue',
  management_consulting: 'rose',
  consulting: 'rose',
  administrative_support: 'gray',
  education: 'yellow',
  healthcare: 'red',
  healthcare_social_assistance: 'red',
  public_administration: 'slate',
  aerospace: 'sky',
  other: 'gray',
};

function getProgressOptionClass(value, selectedValue) {
  const colorName = PROGRESS_STATUS_COLORS[value] || 'gray';
  const activeClass = selectedValue === value ? 'progress-option-active' : '';
  return `progress-option progress-option-${colorName} ${activeClass}`.trim();
}

function getWorkflowBadgeClass(status) {
  const colorName = WORKFLOW_STATUS_COLORS[status] || 'gray';
  return `status-tag status-color-${colorName}`;
}

function getListingStatusClass(status) {
  const normalizedStatus = String(status || 'unknown').trim().toLowerCase();
  const colorName = LISTING_STATUS_COLORS[normalizedStatus] || 'gray';
  return `info-pill status-color-${colorName}`;
}

function getNaicsCategoryClass(category) {
  const normalizedCategory = String(category || 'other').trim().toLowerCase();
  const colorName = NAICS_CATEGORY_COLORS[normalizedCategory] || 'gray';
  return `info-pill naics-tag naics-tag-${colorName}`;
}

function formatDate(value) {
  if (!value) {
    return 'Not provided';
  }

  return new Date(value).toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function ContractDetailPage() {
  const { contractId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const workspaceReturn = location.state?.workspaceReturn;
  const token = localStorage.getItem('token');
  const [contract, setContract] = useState(null);
  const [contractProgress, setContractProgress] = useState('NONE');
  const [workflowStatus, setWorkflowStatus] = useState('NOT_STARTED');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    const loadContractDetail = async () => {
      setLoading(true);
      setError('');

      try {
        const [contractResponse, progressResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/contracts/${contractId}/`, {
            signal: controller.signal,
            headers: token ? { Authorization: `Token ${token}` } : {},
          }),
          fetch(`${API_BASE_URL}/contracts/${contractId}/progress/`, {
            signal: controller.signal,
            headers: token ? { Authorization: `Token ${token}` } : {},
          }),
        ]);

        const contractData = await contractResponse.json();
        const progressData = await progressResponse.json();

        if (!contractResponse.ok) {
          throw new Error(contractData.detail || 'Failed to load contract.');
        }

        if (!progressResponse.ok) {
          throw new Error(progressData.detail || 'Failed to load contract progress.');
        }

        setContract(contractData.contract);
        setContractProgress(progressData.contract_progress || 'NONE');
        setWorkflowStatus(progressData.workflow_status || 'NOT_STARTED');
        setNotes(progressData.notes || '');
      } catch (loadError) {
        if (loadError.name !== 'AbortError') {
          setError(loadError.message || 'Could not load contract details.');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    loadContractDetail();

    return () => controller.abort();
  }, [contractId, token]);

  const handleSaveProgress = async () => {
    setSaving(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/contracts/${contractId}/progress/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Token ${token}`,
        },
        body: JSON.stringify({
          contract_progress: contractProgress,
          workflow_status: workflowStatus,
          notes,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.contract_progress?.[0] || 'Failed to save progress.');
      }

      setContractProgress(data.contract_progress || 'NONE');
      setWorkflowStatus(data.workflow_status || 'NOT_STARTED');
      setNotes(data.notes || '');
      setSuccessMessage('Progress saved.');
    } catch (saveError) {
      setError(saveError.message || 'Could not save progress.');
    } finally {
      setSaving(false);
    }
  };

  const handleBackToContracts = () => {
    navigate(workspaceReturn?.pathname || '/dashboard', {
      state: workspaceReturn ? { restoreWorkspace: workspaceReturn } : undefined,
    });
  };

  const backButtonLabel = workspaceReturn?.pageTitle
    ? `Back to ${workspaceReturn.pageTitle}`
    : 'Back to Dashboard';

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <h2 className="sidebar-title">AI Matchmaking Tool</h2>

        <nav className="sidebar-nav">
          <button className="sidebar-link" onClick={() => navigate('/dashboard')}>
            Dashboard
          </button>
          <button className="sidebar-link" onClick={() => navigate('/ai-matchmaking')}>
            AI Matchmaking
          </button>
          <button className="sidebar-link" onClick={() => navigate('/my-contracts')}>
            My Contracts
          </button>
          <button className="sidebar-link" onClick={() => navigate('/profile')}>
            Profile
          </button>
          <button className="sidebar-link" onClick={() => navigate('/notifications')}>
            Notifications
          </button>
        </nav>
      </aside>

      <div className="dashboard-main">
        <header className="dashboard-topbar">
          <div className="dashboard-inner">
            <button className="notes-cancel-button" onClick={handleBackToContracts}>
              {backButtonLabel}
            </button>
            <div className="topbar-icons">
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
                &#128100;
              </span>
            </div>
          </div>
        </header>

        <main className="dashboard-content">
          <div className="dashboard-inner">
            {loading ? (
              <div className="state-card">Loading contract details...</div>
            ) : error && !contract ? (
              <div className="state-card state-card-error">{error}</div>
            ) : (
              <>
                <h1 className="page-title">{contract.title}</h1>

                {error && <div className="state-card state-card-error detail-message">{error}</div>}

                <section className="section detail-section">
                  <h2 className="section-title">Contract Details</h2>
                  <div className="detail-grid">
                    <div>
                      <span className="detail-label">Agency</span>
                      <p>{contract.agency || 'Not provided'}</p>
                    </div>
                    <div>
                      <span className="detail-label">Sub-agency</span>
                      <p>{contract.sub_agency || 'Not provided'}</p>
                    </div>
                    <div>
                      <span className="detail-label">NAICS</span>
                      <p>
                        <span className={getNaicsCategoryClass(contract.category)}>
                          {contract.naics_code || 'Not provided'}
                        </span>
                      </p>
                    </div>
                    <div>
                      <span className="detail-label">Deadline</span>
                      <p>{formatDate(contract.deadline)}</p>
                    </div>
                    <div>
                      <span className="detail-label">Source</span>
                      <p>{contract.procurement_portal || contract.source || 'Not provided'}</p>
                    </div>
                    <div>
                      <span className="detail-label">Status</span>
                      <p>
                        <span className={getListingStatusClass(contract.status)}>
                          {contract.status || 'Unknown'}
                        </span>
                      </p>
                    </div>
                  </div>

                  <div className="detail-summary">
                    <span className="detail-label">Summary</span>
                    <p>{contract.summary || 'No summary available.'}</p>
                  </div>

                  {contract.hyperlink && (
                    <a className="detail-link" href={contract.hyperlink} target="_blank" rel="noreferrer">
                      Open source listing
                    </a>
                  )}
                </section>

                <section className="section detail-section">
                  <h2 className="section-title">Progress</h2>
                  {successMessage && <div className="state-card detail-success-message">{successMessage}</div>}
                  <div className="progress-control-group">
                    {PROGRESS_OPTIONS.map((option) => (
                      <label
                        key={option.value}
                        className={getProgressOptionClass(option.value, contractProgress)}
                      >
                        <input
                          type="radio"
                          name="contract-progress"
                          value={option.value}
                          checked={contractProgress === option.value}
                          onChange={(event) => setContractProgress(event.target.value)}
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>

                  <label className="status-label" htmlFor="workflowStatus">
                    Workflow status
                  </label>
                  <select
                    id="workflowStatus"
                    className="status-select detail-workflow-select"
                    value={workflowStatus}
                    onChange={(event) => setWorkflowStatus(event.target.value)}
                  >
                    {WORKFLOW_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <span className={getWorkflowBadgeClass(workflowStatus)}>
                    {WORKFLOW_OPTIONS.find((option) => option.value === workflowStatus)?.label || workflowStatus}
                  </span>

                  <label className="status-label" htmlFor="contractNotes">
                    Notes
                  </label>
                  <textarea
                    id="contractNotes"
                    className="notes-textarea"
                    rows="7"
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    placeholder="Add private notes for this contract..."
                  />

                  <button
                    className="notes-save-button detail-save-button"
                    onClick={handleSaveProgress}
                    disabled={saving || !token}
                  >
                    {saving ? 'Saving...' : 'Save Progress'}
                  </button>
                </section>
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default ContractDetailPage;
