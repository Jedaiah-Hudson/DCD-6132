import './DashboardPage.css';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const initialContracts = [
  {
    id: 1,
    title: 'Cybersecurity Infrastructure Enhancement',
    agency: 'Department of Defense',
    subAgency: 'Defense Information Systems Agency',
    naics: '541512',
    dueDate: 'March 15, 2026',
    category: 'Prime',
    partner: 'Northwind Systems',
    senderCompany: 'Northwind Systems',
    source: 'Email',
    hyperlink: 'https://example.com/cybersecurity-infrastructure-enhancement',
    status: 'Reviewing',
    notes: 'Strong match for existing cybersecurity experience.',
    summary:
      'Enhance cybersecurity infrastructure across multiple defense systems, focusing on threat detection and system resilience.',
  },
  {
    id: 2,
    title: 'Medical Equipment Manufacturing Contract',
    agency: 'Department of Health & Human Services',
    subAgency: 'Office of the Assistant Secretary for Preparedness and Response',
    naics: '339112',
    dueDate: 'March 22, 2026',
    category: 'Subcontract',
    partner: 'Apex Health Manufacturing',
    senderCompany: 'Apex Health Manufacturing',
    source: 'Procurement',
    hyperlink: 'https://example.com/medical-equipment-manufacturing-contract',
    status: 'Not Started',
    notes: '',
    summary:
      'Manufacture and supply medical equipment for federal healthcare programs with strict compliance requirements.',
  },
  {
    id: 3,
    title: 'Industrial Equipment Maintenance Services',
    agency: 'General Services Administration',
    subAgency: 'Public Buildings Service',
    naics: '811310',
    dueDate: 'April 5, 2026',
    category: 'Prime',
    partner: 'Atlas Industrial Group',
    senderCompany: 'Atlas Industrial Group',
    source: 'Procurement',
    hyperlink: 'https://example.com/industrial-equipment-maintenance-services',
    status: 'Submitted',
    notes: 'Follow up on required maintenance certifications.',
    summary:
      'Provide ongoing maintenance and repair services for industrial equipment across federal facilities.',
  },
  {
    id: 4,
    title: 'Healthcare IT System Implementation',
    agency: 'Veterans Affairs',
    subAgency: 'Veterans Health Administration',
    naics: '541519',
    dueDate: 'April 12, 2026',
    category: 'Prime',
    partner: 'Northwind Systems',
    senderCompany: 'Northwind Systems',
    source: 'Email',
    hyperlink: 'https://example.com/healthcare-it-system-implementation',
    status: 'Drafting',
    notes: '',
    summary:
      'Implement and integrate healthcare IT systems to improve patient data management and operational efficiency.',
  },
];

const categories = [
  { name: 'Cybersecurity', count: 24 },
  { name: 'Manufacturing', count: 18 },
  { name: 'Industrial', count: 15 },
  { name: 'Healthcare', count: 21 },
];

const recentHistory = [
  {
    id: 1,
    agency: 'Department of Defense',
    naics: '541512',
    category: 'Prime',
    dueDate: 'Feb 28, 2026',
  },
  {
    id: 2,
    agency: 'GSA',
    naics: '541611',
    category: 'Subcontract',
    dueDate: 'Feb 25, 2026',
  },
  {
    id: 3,
    agency: 'Department of Energy',
    naics: '221114',
    category: 'Partnership',
    dueDate: 'Feb 20, 2026',
  },
];

const statusOptions = ['Not Started', 'Reviewing', 'Drafting', 'Submitted'];

function DashboardPage() {
  const navigate = useNavigate();
  const [hoveredId, setHoveredId] = useState(null);
  const [selectedContractId, setSelectedContractId] = useState(null);
  const [contracts, setContracts] = useState(initialContracts);
  const [selectedPartner, setSelectedPartner] = useState('All Partners');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');
  const [lastSynced, setLastSynced] = useState('April 6, 2026 at 10:25 AM');
  const [activeNoteId, setActiveNoteId] = useState(null);
  const [draftNotes, setDraftNotes] = useState({});

  const partnerOptions = useMemo(() => {
    const partners = Array.from(new Set(initialContracts.map((contract) => contract.partner)));
    return ['All Partners', ...partners];
  }, []);

  const filteredContracts = useMemo(() => {
    if (selectedPartner === 'All Partners') {
      return contracts;
    }

    return contracts.filter((contract) => contract.partner === selectedPartner);
  }, [contracts, selectedPartner]);

  const selectedContract =
    filteredContracts.find((contract) => contract.id === selectedContractId) || null;

  const handleSyncContracts = () => {
    setIsSyncing(true);
    setSyncMessage('');

    window.setTimeout(() => {
      setIsSyncing(false);
      setLastSynced('April 6, 2026 at 10:42 AM');
      setSyncMessage('Contracts synced successfully.');
    }, 1200);
  };

  const handleStatusChange = (contractId, nextStatus) => {
    setContracts((currentContracts) =>
      currentContracts.map((contract) =>
        contract.id === contractId ? { ...contract, status: nextStatus } : contract
      )
    );
  };

  const handleOpenNotes = (contract) => {
    setActiveNoteId(contract.id);
    setDraftNotes((currentDrafts) => ({
      ...currentDrafts,
      [contract.id]: currentDrafts[contract.id] ?? contract.notes,
    }));
  };

  const handleSaveNote = (contractId) => {
    setContracts((currentContracts) =>
      currentContracts.map((contract) =>
        contract.id === contractId
          ? { ...contract, notes: draftNotes[contractId] || '' }
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
    return source === 'Procurement' ? 'source-label procurement-source' : 'source-label email-source';
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

              <div className="contract-list">
                {filteredContracts.map((contract) => (
                  <div
                    key={contract.id}
                    className={`contract-card ${
                      selectedContractId === contract.id ? 'selected-contract-card' : ''
                    }`}
                    onClick={() => setSelectedContractId(contract.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="card-heading-row">
                      <div>
                        <div className="title-row">
                          <h3>{contract.title}</h3>

                          <span
                            className="summary-button"
                            onMouseEnter={() => setHoveredId(contract.id)}
                            onMouseLeave={() => setHoveredId(null)}
                            onClick={(event) => event.stopPropagation()}
                          >
                            View Summary
                          </span>
                        </div>

                        {hoveredId === contract.id && (
                          <div className="summary-popup">
                            {contract.summary}
                          </div>
                        )}

                        <div className="card-meta-row">
                          <span className={getSourceClassName(contract.source)}>{contract.source}</span>
                          <span className="partner-pill">Partner: {contract.partner}</span>
                          <span className="contract-tag">{contract.category}</span>
                        </div>
                      </div>

                      <div
                        className="contract-status-block"
                        onClick={(event) => event.stopPropagation()}
                      >
                        <label htmlFor={`status-${contract.id}`} className="status-label">
                          Status
                        </label>
                        <select
                          id={`status-${contract.id}`}
                          className="status-select"
                          value={contract.status}
                          onChange={(event) => handleStatusChange(contract.id, event.target.value)}
                        >
                          {statusOptions.map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>
                        <span className={getStatusClassName(contract.status)}>{contract.status}</span>
                      </div>
                    </div>

                    <p>
                      <strong>Agency:</strong> {contract.agency}
                    </p>
                    <p>
                      <strong>NAICS Code:</strong> {contract.naics}
                    </p>
                    <p>
                      <strong>Due Date:</strong> {contract.dueDate}
                    </p>

                    <div
                      className="notes-section"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <div className="notes-header-row">
                        <h4 className="notes-title">Notes</h4>
                        <button
                          className="note-action-button"
                          onClick={() => handleOpenNotes(contract)}
                        >
                          {contract.notes ? 'Edit Note' : 'Add Note'}
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
                          {contract.notes || 'No notes added yet.'}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="section">
              <h2 className="section-title">Quick Browse</h2>
              <div className="browse-grid">
                {categories.map((category) => (
                  <div key={category.name} className="browse-card">
                    <h3>{category.name}</h3>
                    <p>{category.count} opportunities</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="section">
              <h2 className="section-title">Recent Contract History</h2>
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
                        <td>{item.agency}</td>
                        <td>{item.naics}</td>
                        <td>{item.category}</td>
                        <td>{item.dueDate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </main>
      </div>

      {selectedContract && (
        <div
          className="contract-modal-overlay"
          onClick={() => setSelectedContractId(null)}
        >
          <div
            className="contract-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="contract-modal-header">
              <h2 className="section-title">Contract Details</h2>
              <button
                className="contract-modal-close"
                onClick={() => setSelectedContractId(null)}
              >
                Close
              </button>
            </div>

            <h3 className="expanded-contract-title">{selectedContract.title}</h3>

            <p>
              <strong>Summary:</strong> {selectedContract.summary}
            </p>
            <p>
              <strong>Sender/Company:</strong> {selectedContract.senderCompany}
            </p>
            <p>
              <strong>Deadline:</strong> {selectedContract.dueDate}
            </p>
            <p>
              <strong>Agency:</strong> {selectedContract.agency}
            </p>
            <p>
              <strong>Sub-Agency:</strong> {selectedContract.subAgency}
            </p>
            <p>
              <strong>NAICS Code:</strong> {selectedContract.naics}
            </p>
            <p>
              <strong>Source:</strong> {selectedContract.source}
            </p>
            <p>
              <strong>Hyperlink:</strong>{' '}
              <a href={selectedContract.hyperlink} target="_blank" rel="noreferrer">
                View Opportunity
              </a>
            </p>
            <p>
              <strong>Status:</strong> {selectedContract.status || 'N/A'}
            </p>
            <p>
              <strong>Notes:</strong> {selectedContract.notes || 'No notes available.'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default DashboardPage;