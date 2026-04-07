import './DashboardPage.css';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const OPPORTUNITIES_API_URL = 'http://127.0.0.1:8000/api/opportunities/';

const formatLastSynced = () =>
  new Date().toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

const buildOpportunitiesUrl = (searchTerm, naicsCode) => {
  const url = new URL(OPPORTUNITIES_API_URL);

  if (searchTerm.trim()) {
    url.searchParams.set('search', searchTerm.trim());
  }

  if (naicsCode) {
    url.searchParams.set('naics_code', naicsCode);
  }

  return url.toString();
};

async function fetchOpportunities(searchTerm, naicsCode, signal) {
  const response = await fetch(buildOpportunitiesUrl(searchTerm, naicsCode), { signal });

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

function DashboardPage() {
  const navigate = useNavigate();
  const [hoveredId, setHoveredId] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [allOpportunities, setAllOpportunities] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedNaics, setSelectedNaics] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSynced, setLastSynced] = useState('Not synced yet');

  useEffect(() => {
    const controller = new AbortController();

    const loadFilterOptions = async () => {
      try {
        const data = await fetchOpportunities('', '', controller.signal);
        setAllOpportunities(data);
        setLastSynced(formatLastSynced());
      } catch (fetchError) {
        if (fetchError.name === 'AbortError') {
          return;
        }
      }
    };

    loadFilterOptions();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    const loadVisibleOpportunities = async () => {
      setLoading(true);
      setError('');

      try {
        const data = await fetchOpportunities(searchTerm, selectedNaics, controller.signal);
        setOpportunities(data);

        if (!searchTerm.trim() && !selectedNaics) {
          setAllOpportunities(data);
          setLastSynced(formatLastSynced());
        }
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
        setOpportunities([]);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    loadVisibleOpportunities();

    return () => controller.abort();
  }, [searchTerm, selectedNaics]);

  const naicsOptions = useMemo(() => {
    return Array.from(
      new Set(
        allOpportunities
          .map((opportunity) => opportunity.naics_code)
          .filter(Boolean)
      )
    ).sort();
  }, [allOpportunities]);

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

  const recentOpportunities = useMemo(() => opportunities.slice(0, 3), [opportunities]);

  const handleSyncContracts = async () => {
    setIsSyncing(true);
    setError('');

    try {
      const [catalogData, visibleData] = await Promise.all([
        fetchOpportunities('', ''),
        fetchOpportunities(searchTerm, selectedNaics),
      ]);

      setAllOpportunities(catalogData);
      setOpportunities(visibleData);
      setLastSynced(formatLastSynced());
    } catch (fetchError) {
      const isNetworkError = fetchError instanceof TypeError;
      setError(
        isNetworkError
          ? 'Could not connect to the server.'
          : fetchError.message || 'Failed to load opportunities.'
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
                  <p className="section-helper-text">Filter live opportunities by NAICS code and review the matching results.</p>
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
              </div>

              {loading ? (
                <div className="state-card">Loading opportunities...</div>
              ) : error ? (
                <div className="state-card state-card-error">{error}</div>
              ) : opportunities.length === 0 ? (
                <div className="state-card">No opportunities match the selected filters.</div>
              ) : (
                <div className="contract-list">
                  {opportunities.map((opportunity) => (
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
                          </div>
                        </div>
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
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="section">
              <h2 className="section-title">Quick Browse</h2>
              {quickBrowseItems.length === 0 ? (
                <div className="state-card">No NAICS data available yet.</div>
              ) : (
                <div className="browse-grid">
                  {quickBrowseItems.map((item) => (
                    <div key={item.code} className="browse-card">
                      <h3>{item.code}</h3>
                      <p>{item.count} opportunities</p>
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
