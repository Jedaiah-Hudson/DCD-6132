import './DashboardPage.css';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const OPPORTUNITIES_API_URL = 'http://127.0.0.1:8000/api/opportunities/';
const PROGRESS_SUMMARY_API_URL = 'http://127.0.0.1:8000/api/contract-progress/summary/';
const STATUS_OPTIONS = ['Not Started', 'Reviewing', 'Drafting', 'Submitted'];

const formatLastSynced = () =>
  new Date().toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

  const SAM_SYNC_URL = 'http://127.0.0.1:8000/api/sam/sync/';

async function syncSamOpportunities(limit = 10) {
  const response = await fetch(SAM_SYNC_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ limit }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || 'Sync failed');
  }

  return data;
}

async function fetchOpportunities(signal, token) {
  const headers = token ? { Authorization: `Token ${token}` } : {};
  const response = await fetch(OPPORTUNITIES_API_URL, { signal, headers });

  let data = [];
  try {
    data = await response.json();
  } catch {
    data = [];
  }

  if (!response.ok) {
    throw new Error('Failed to load opportunities.');
  }

  if (!Array.isArray(data)) {
    throw new Error('Unexpected response from the server.');
  }

  return data;
}

async function fetchProgressSummary(signal, token) {
  if (!token) {
    return { won: 0, lost: 0, pending: 0, tracked: 0 };
  }

  const response = await fetch(PROGRESS_SUMMARY_API_URL, {
    signal,
    headers: {
      Authorization: `Token ${token}`,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Failed to load progress summary.');
  }

  return data;
}

function DashboardPage() {
  const navigate = useNavigate();
  const [hoveredId, setHoveredId] = useState(null);
  const [allOpportunities, setAllOpportunities] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedNaics, setSelectedNaics] = useState('');
  const [selectedAgency, setSelectedAgency] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSynced, setLastSynced] = useState('Not synced yet');
  const [progressSummary, setProgressSummary] = useState({
    won: 0,
    lost: 0,
    pending: 0,
    tracked: 0,
  });
  const token = localStorage.getItem('token');

  useEffect(() => {
    const controller = new AbortController();

    const loadOpportunities = async () => {
      setLoading(true);
      setError('');

      try {
        const [data, summary] = await Promise.all([
          fetchOpportunities(controller.signal, token),
          fetchProgressSummary(controller.signal, token),
        ]);
        setAllOpportunities(data);
        setProgressSummary(summary);
        setLastSynced(formatLastSynced());
      } catch (fetchError) {
        if (fetchError.name === 'AbortError') {
          return;
        }

        const isNetworkError = fetchError instanceof TypeError;
        setError(
          isNetworkError
            ? 'Could not connect to the server.'
            : fetchError.message || 'Failed to load opportunities.'
        );
        setAllOpportunities([]);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    loadOpportunities();

    return () => controller.abort();
  }, [token]);

  const agencyOptions = useMemo(() => {
    return Array.from(
      new Set(
        allOpportunities
          .map((opportunity) => opportunity.agency)
          .filter(Boolean)
      )
    ).sort((left, right) => left.localeCompare(right));
  }, [allOpportunities]);

  const naicsOptions = useMemo(() => {
    return Array.from(
      new Set(
        allOpportunities
          .map((opportunity) => opportunity.naics_code)
          .filter(Boolean)
      )
    ).sort();
  }, [allOpportunities]);

  const filteredOpportunities = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const normalizedAgency = selectedAgency.trim().toLowerCase();
    const normalizedStatus = selectedStatus.trim().toLowerCase();

    return allOpportunities.filter((opportunity) => {
      const searchableText = [
        opportunity.title,
        opportunity.agency,
        opportunity.description,
        opportunity.partner,
        opportunity.status,
        opportunity.naics_code,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      const opportunityAgency = String(opportunity.agency || '').trim().toLowerCase();
      const opportunityStatus = String(opportunity.status || '').trim().toLowerCase();
      const opportunityNaics = String(opportunity.naics_code || '').trim();

      const matchesSearch = !normalizedSearch || searchableText.includes(normalizedSearch);
      const matchesAgency = !normalizedAgency || opportunityAgency === normalizedAgency;
      const matchesStatus = !normalizedStatus || opportunityStatus === normalizedStatus;
      const matchesNaics = !selectedNaics || opportunityNaics === selectedNaics;

      return matchesSearch && matchesAgency && matchesStatus && matchesNaics;
    });
  }, [allOpportunities, searchTerm, selectedAgency, selectedStatus, selectedNaics]);

  const quickBrowseItems = useMemo(() => {
    const countsByNaics = allOpportunities.reduce((counts, opportunity) => {
      const code = opportunity.naics_code;
      if (!code) {
        return counts;
      }

      counts.set(code, (counts.get(code) || 0) + 1);
      return counts;
    }, new Map());

    return Array.from(countsByNaics.entries())
      .sort((left, right) => {
        if (right[1] !== left[1]) {
          return right[1] - left[1];
        }

        return left[0].localeCompare(right[0]);
      })
      .slice(0, 4)
      .map(([code, count]) => ({ code, count }));
  }, [allOpportunities]);

  const recentOpportunities = useMemo(() => filteredOpportunities.slice(0, 3), [filteredOpportunities]);

  const handleSyncContracts = async () => {
    if (isSyncing) {
      return;
    }

    setIsSyncing(true);
    setError('');

    try {
    const result = await syncSamOpportunities(10);

    // after sync finishes, reload opportunities from DB
    const [catalogData, summaryData] = await Promise.all([
      fetchOpportunities(undefined, token),
      fetchProgressSummary(undefined, token),
    ]);

    setAllOpportunities(catalogData);
    setProgressSummary(summaryData);
    setLastSynced(formatLastSynced());

    console.log('Sync result:', result);
  } catch (fetchError) {
    const isNetworkError = fetchError instanceof TypeError;

    setError(
      isNetworkError
        ? 'Could not connect to the server.'
        : fetchError.message || 'Sync failed.'
    );
  } finally {
    setIsSyncing(false);
  }
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
            <input
              type="text"
              placeholder="Search opportunities..."
              className="search-bar"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
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

            <section className="section progress-summary-section">
              <div className="progress-summary-card">
                <span className="progress-summary-label">Tracked</span>
                <strong>{progressSummary.tracked}</strong>
              </div>
              <div className="progress-summary-card">
                <span className="progress-summary-label">Pending</span>
                <strong>{progressSummary.pending}</strong>
              </div>
              <div className="progress-summary-card">
                <span className="progress-summary-label">Won</span>
                <strong>{progressSummary.won}</strong>
              </div>
              <div className="progress-summary-card">
                <span className="progress-summary-label">Lost</span>
                <strong>{progressSummary.lost}</strong>
              </div>
            </section>

            <section className="section sync-section">
              <div className="sync-header-row">
                <div>
                  <h2 className="section-title">Contract Sync</h2>
                  <p className="section-helper-text">Load the latest backend opportunities and refresh the dashboard.</p>
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
                {!error && !loading && <p className="sync-success-text">Showing live backend opportunities.</p>}
              </div>
            </section>

            <section className="section">
              <div className="section-heading-row">
                <div>
                  <h2 className="section-title">For You</h2>
                  <p className="section-helper-text">Filter live opportunities by agency, status, NAICS code, and search terms.</p>
                </div>
                <div className="filter-group">
                  <label htmlFor="agencyFilter" className="filter-label">
                    Agency
                  </label>
                  <select
                    id="agencyFilter"
                    className="partner-filter"
                    value={selectedAgency}
                    onChange={(event) => setSelectedAgency(event.target.value)}
                  >
                    <option value="">All Agencies</option>
                    {agencyOptions.map((agency) => (
                      <option key={agency} value={agency}>
                        {agency}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="filter-group">
                  <label htmlFor="naicsFilter" className="filter-label">
                    NAICS Code
                  </label>
                  <select
                    id="naicsFilter"
                    className="partner-filter"
                    value={selectedNaics}
                    onChange={(event) => setSelectedNaics(event.target.value)}
                  >
                    <option value="">All NAICS</option>
                    {naicsOptions.map((naicsCode) => (
                      <option key={naicsCode} value={naicsCode}>
                        {naicsCode}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="filter-group">
                  <label htmlFor="statusFilter" className="filter-label">
                    Status
                  </label>
                  <select
                    id="statusFilter"
                    className="partner-filter"
                    value={selectedStatus}
                    onChange={(event) => setSelectedStatus(event.target.value)}
                  >
                    <option value="">All Statuses</option>
                    {STATUS_OPTIONS.map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {loading ? (
                <div className="state-card">Loading opportunities...</div>
              ) : error ? (
                <div className="state-card state-card-error">{error}</div>
              ) : filteredOpportunities.length === 0 ? (
                <div className="state-card">No opportunities match the selected filters.</div>
              ) : (
                <div className="contract-list">
                  {filteredOpportunities.map((opportunity) => (
                    <div key={opportunity.id} className="contract-card">
                      <div className="card-heading-row">
                        <div>
                          <div className="title-row">
                            <h3>{opportunity.title}</h3>
                            <span
                              className="summary-button"
                              onMouseEnter={() => setHoveredId(opportunity.id)}
                              onMouseLeave={() => setHoveredId(null)}
                            >
                              View Summary
                            </span>
                          </div>
                          {hoveredId === opportunity.id && (
                            <div className="summary-popup">
                              {opportunity.description || 'No summary available.'}
                            </div>
                          )}
                          <div className="card-meta-row">
                            <span className="contract-tag">NAICS {opportunity.naics_code}</span>
                            {opportunity.agency && (
                              <span className="partner-pill">{opportunity.agency}</span>
                            )}
                            {opportunity.status && (
                              <span className="status-tag status-tag-neutral">{opportunity.status}</span>
                            )}
                            {opportunity.contract_progress && opportunity.contract_progress !== 'NONE' && (
                              <span className="status-tag status-tag-neutral">
                                {opportunity.contract_progress}
                              </span>
                            )}
                          </div>
                        </div>
                        <button
                          className="note-action-button"
                          type="button"
                          onClick={() => navigate(`/contracts/${opportunity.id}`)}
                        >
                          View Details
                        </button>
                      </div>

                      <p>
                        <strong>Agency:</strong> {opportunity.agency || 'Not provided'}
                      </p>
                      <p>
                        <strong>NAICS Code:</strong> {opportunity.naics_code}
                      </p>
                      <p>
                        <strong>Description:</strong> {opportunity.description || 'No description provided.'}
                      </p>
                      <p>
                        <strong>Status:</strong> {opportunity.status || 'Not Started'}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </section>

          

            <section className="section">
              <h2 className="section-title">Recent Opportunities</h2>
              {recentOpportunities.length === 0 ? (
                <div className="state-card">No opportunities available for the current filters.</div>
              ) : (
                <div className="history-table-wrapper">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Title</th>
                        <th>Agency</th>
                        <th>NAICS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentOpportunities.map((opportunity) => (
                        <tr key={opportunity.id}>
                          <td>{opportunity.title}</td>
                          <td>{opportunity.agency || 'Not provided'}</td>
                          <td>{opportunity.naics_code}</td>
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
