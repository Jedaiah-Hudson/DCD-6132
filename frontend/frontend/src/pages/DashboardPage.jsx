import './DashboardPage.css';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const statusOptions = ['Not Started', 'Reviewing', 'Drafting', 'Submitted'];
const sourceLabelMap = {
  gmail: 'Email',
  outlook: 'Email',
  procurement: 'Procurement',
};
const sourceClassMap = {
  gmail: 'source-label email-source',
  outlook: 'source-label email-source',
  procurement: 'source-label procurement-source',
};

function DashboardPage() {
  const navigate = useNavigate();
  const [contracts, setContracts] = useState([]);
  const [selectedPartner, setSelectedPartner] = useState('All Partners');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');
  const [lastSynced, setLastSynced] = useState('Not synced yet');
  const [activeNoteId, setActiveNoteId] = useState(null);
  const [draftNotes, setDraftNotes] = useState({});
  const [isLoadingContracts, setIsLoadingContracts] = useState(true);
  const [contractsError, setContractsError] = useState('');

  const token = localStorage.getItem('token');

  const partnerOptions = useMemo(() => {
    const partners = Array.from(
      new Set(
        contracts
          .map((contract) => contract.partner_name || contract.partner || '')
          .filter(Boolean)
      )
    ).sort((a, b) => a.localeCompare(b));

    return ['All Partners', ...partners];
  }, [contracts]);

  const filteredContracts = useMemo(() => {
    if (selectedPartner === 'All Partners') {
      return contracts;
    }

    return contracts.filter(
      (contract) => (contract.partner_name || contract.partner || '') === selectedPartner
    );
  }, [contracts, selectedPartner]);

  const categories = useMemo(() => {
    const counts = filteredContracts.reduce((accumulator, contract) => {
      const key = contract.category || 'Uncategorized';
      accumulator[key] = (accumulator[key] || 0) + 1;
      return accumulator;
    }, {});

    return Object.entries(counts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 4);
  }, [filteredContracts]);

  const recentHistory = useMemo(() => {
    return [...filteredContracts]
      .sort((a, b) => {
        const aTime = a.deadline ? new Date(a.deadline).getTime() : Number.MAX_SAFE_INTEGER;
        const bTime = b.deadline ? new Date(b.deadline).getTime() : Number.MAX_SAFE_INTEGER;
        return aTime - bTime;
      })
      .slice(0, 5);
  }, [filteredContracts]);

  const parseJsonResponse = async (response) => {
    const text = await response.text();
    return text ? JSON.parse(text) : {};
  };

  const formatDeadline = (deadline) => {
    if (!deadline) {
      return 'No deadline listed';
    }

    const date = new Date(deadline);

    if (Number.isNaN(date.getTime())) {
      return 'No deadline listed';
    }

    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const fetchContracts = async ({ showLoader = true, showSuccess = false } = {}) => {
    if (showLoader) {
      setIsLoadingContracts(true);
    }

    setContractsError('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/contracts/`, {
        headers: token ? { Authorization: `Token ${token}` } : {},
      });
      const data = await parseJsonResponse(response);

      if (!response.ok) {
        setContractsError(data.error || 'Failed to load contracts.');
        return;
      }

      const nextContracts = Array.isArray(data.contracts) ? data.contracts : [];
      setContracts(
        nextContracts.map((contract) => ({
          ...contract,
          localStatus: contract.status || 'Not Started',
          localNotes: contract.localNotes || '',
        }))
      );
      setLastSynced(new Date().toLocaleString());

      if (showSuccess) {
        setSyncMessage('Contracts synced successfully.');
      }
    } catch (error) {
      setContractsError('Could not connect to the contracts service.');
    } finally {
      if (showLoader) {
        setIsLoadingContracts(false);
      }
    }
  };

  useEffect(() => {
    fetchContracts();
  }, []);

  useEffect(() => {
    if (!partnerOptions.includes(selectedPartner)) {
      setSelectedPartner('All Partners');
    }
  }, [partnerOptions, selectedPartner]);

  const handleSyncContracts = async () => {
    setIsSyncing(true);
    setSyncMessage('');
    await fetchContracts({ showLoader: false, showSuccess: true });
    setIsSyncing(false);
  };

  const handleStatusChange = (contractId, nextStatus) => {
    setContracts((currentContracts) =>
      currentContracts.map((contract) =>
        contract.id === contractId ? { ...contract, localStatus: nextStatus } : contract
      )
    );
  };

  const handleOpenNotes = (contract) => {
    setActiveNoteId(contract.id);
    setDraftNotes((currentDrafts) => ({
      ...currentDrafts,
      [contract.id]: currentDrafts[contract.id] ?? contract.localNotes ?? '',
    }));
  };

  const handleSaveNote = (contractId) => {
    setContracts((currentContracts) =>
      currentContracts.map((contract) =>
        contract.id === contractId
          ? { ...contract, localNotes: draftNotes[contractId] || '' }
          : contract
      )
    );
    setActiveNoteId(null);
  };

  const getStatusClassName = (status) => {
    if (status === 'Submitted') {
      return 'status-tag status-tag-submitted';
    }

    if (status === 'Drafting') {
      return 'status-tag status-tag-drafting';
    }

    if (status === 'Reviewing') {
      return 'status-tag status-tag-reviewing';
    }

    return 'status-tag status-tag-neutral';
  };

  const getSourceClassName = (source) => {
    return sourceClassMap[source] || 'source-label email-source';
  };

  const getSourceText = (source) => {
    return sourceLabelMap[source] || source || 'Email';
  };

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <h2 className="sidebar-title">AI Matchmaking Tool</h2>

        <nav className="sidebar-nav">
          <button className="sidebar-link active" onClick={() => navigate('/dashboard')}>
            Dashboard
          </button>
          <button className="sidebar-link" onClick={() => navigate('/dashboard')}>
            AI Matchmaking
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
            <input type="text" placeholder="Search contracts..." className="search-bar" />
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
                👤
              </span>
            </div>
          </div>
        </header>

        <main className="dashboard-content">
          <div className="dashboard-inner">
            <h1 className="page-title">Dashboard</h1>

            <section className="section sync-section">
              <div className="sync-header-row">
                <div>
                  <h2 className="section-title">Contract Sync</h2>
                  <p className="section-helper-text">Sync the latest opportunities from connected sources.</p>
                </div>
                <button
                  className="sync-button"
                  onClick={handleSyncContracts}
                  disabled={isSyncing}
                >
                  {isSyncing ? 'Syncing...' : 'Sync Contracts'}
                </button>
              </div>

              <div className="sync-feedback-row">
                <p className="sync-meta-text">Last synced: {lastSynced}</p>
                {syncMessage && <p className="sync-success-text">{syncMessage}</p>}
              </div>
            </section>

            <section className="section">
              <div className="section-heading-row">
                <div>
                  <h2 className="section-title">For You</h2>
                  <p className="section-helper-text">Filter by partner and review source, notes, and contract status.</p>
                </div>
                <div className="filter-group">
                  <label htmlFor="partnerFilter" className="filter-label">
                    Partner
                  </label>
                  <select
                    id="partnerFilter"
                    className="partner-filter"
                    value={selectedPartner}
                    onChange={(event) => setSelectedPartner(event.target.value)}
                  >
                    {partnerOptions.map((partner) => (
                      <option key={partner} value={partner}>
                        {partner}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {contractsError && <p className="dashboard-error-text">{contractsError}</p>}
              {isLoadingContracts ? (
                <div className="empty-state-card">Loading contracts...</div>
              ) : filteredContracts.length === 0 ? (
                <div className="empty-state-card">No contracts available for this partner yet.</div>
              ) : (
                <div className="contract-list">
                  {filteredContracts.map((contract) => (
                    <div key={contract.id} className="contract-card">
                      <div className="card-heading-row">
                        <div>
                          <h3>{contract.title}</h3>
                          <div className="card-meta-row">
                            <span className={getSourceClassName(contract.source)}>{getSourceText(contract.source)}</span>
                            {!!(contract.partner_name || contract.partner) && (
                              <span className="partner-pill">Partner: {contract.partner_name || contract.partner}</span>
                            )}
                            <span className="contract-tag">{contract.category || 'Uncategorized'}</span>
                          </div>
                        </div>
                        <div className="contract-status-block">
                          <label htmlFor={`status-${contract.id}`} className="status-label">
                            Status
                          </label>
                          <select
                            id={`status-${contract.id}`}
                            className="status-select"
                            value={contract.localStatus || 'Not Started'}
                            onChange={(event) => handleStatusChange(contract.id, event.target.value)}
                          >
                            {statusOptions.map((status) => (
                              <option key={status} value={status}>
                                {status}
                              </option>
                            ))}
                          </select>
                          <span className={getStatusClassName(contract.localStatus || 'Not Started')}>
                            {contract.localStatus || 'Not Started'}
                          </span>
                        </div>
                      </div>

                      <p>
                        <strong>Agency:</strong> {contract.agency || 'Unknown agency'}
                      </p>
                      {contract.summary && (
                        <p>
                          <strong>Summary:</strong> {contract.summary}
                        </p>
                      )}
                      <p>
                        <strong>NAICS Code:</strong> {contract.naics_code || 'Not listed'}
                      </p>
                      <p>
                        <strong>Due Date:</strong> {formatDeadline(contract.deadline)}
                      </p>

                      <div className="notes-section">
                        <div className="notes-header-row">
                          <h4 className="notes-title">Notes</h4>
                          <button
                            className="note-action-button"
                            onClick={() => handleOpenNotes(contract)}
                          >
                            {contract.localNotes ? 'Edit Note' : 'Add Note'}
                          </button>
                        </div>

                        {activeNoteId === contract.id ? (
                          <div className="notes-editor">
                            <textarea
                              className="notes-textarea"
                              rows="4"
                              value={draftNotes[contract.id] || ''}
                              onChange={(event) =>
                                setDraftNotes((currentDrafts) => ({
                                  ...currentDrafts,
                                  [contract.id]: event.target.value,
                                }))
                              }
                              placeholder="Add notes about this contract..."
                            />
                            <div className="notes-editor-actions">
                              <button
                                className="notes-save-button"
                                onClick={() => handleSaveNote(contract.id)}
                              >
                                Save Note
                              </button>
                              <button
                                className="notes-cancel-button"
                                onClick={() => setActiveNoteId(null)}
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="notes-display-box">
                            {contract.localNotes || 'No notes added yet.'}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="section">
              <h2 className="section-title">Quick Browse</h2>
              {categories.length === 0 ? (
                <div className="empty-state-card">Categories will appear once contracts are available.</div>
              ) : (
                <div className="browse-grid">
                  {categories.map((category) => (
                    <div key={category.name} className="browse-card">
                      <h3>{category.name}</h3>
                      <p>{category.count} opportunities</p>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="section">
              <h2 className="section-title">Recent Contract History</h2>
              {recentHistory.length === 0 ? (
                <div className="empty-state-card">Recent contract history will appear after contracts load.</div>
              ) : (
                <div className="history-table-wrapper">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Agency</th>
                        <th>NAICS</th>
                        <th>Category</th>
                        <th>Due Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentHistory.map((item) => (
                        <tr key={item.id}>
                          <td>{item.agency || 'Unknown agency'}</td>
                          <td>{item.naics_code || 'Not listed'}</td>
                          <td>{item.category || 'Uncategorized'}</td>
                          <td>{formatDeadline(item.deadline)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}

export default DashboardPage;
