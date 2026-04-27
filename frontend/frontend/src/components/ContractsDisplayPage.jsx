import '../pages/DashboardPage.css';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import useNotificationSummary from '../hooks/useNotificationSummary';

const OPPORTUNITIES_API_URL = 'http://127.0.0.1:8000/api/opportunities/';
const PROGRESS_SUMMARY_API_URL = 'http://127.0.0.1:8000/api/contract-progress/summary/';
const LISTING_STATUS_COLORS = {
  active: 'green',
  inactive: 'gray',
  unknown: 'gray',
  reviewing: 'amber',
  drafting: 'blue',
  submitted: 'green',
};
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
const RELATIONSHIP_LABEL_COLORS = {
  UNASSIGNED: 'gray',
  PRIME: 'green',
  SUBCONTRACTOR: 'blue',
  TEAMING: 'purple',
  VENDOR: 'amber',
  CONSULTANT: 'teal',
};
const PROGRESS_STATUS_LABELS = {
  NONE: 'Not tracked',
  PENDING: 'Pending',
  WON: 'Won',
  LOST: 'Lost',
};
const WORKFLOW_STATUS_LABELS = {
  NOT_STARTED: 'Not Started',
  REVIEWING: 'Reviewing',
  DRAFTING: 'Drafting',
  SUBMITTED: 'Submitted',
};
const RELATIONSHIP_LABELS = {
  UNASSIGNED: 'Unassigned',
  PRIME: 'Prime',
  SUBCONTRACTOR: 'Sub',
  TEAMING: 'Teaming',
  VENDOR: 'Vendor',
  CONSULTANT: 'Consultant',
};
const NAICS_CATEGORY_COLORS = {
  agriculture: 'green',
  mining_energy: 'amber',
  utilities: 'cyan',
  construction: 'orange',
  manufacturing: 'indigo',
  wholesale: 'slate',
  retail: 'pink',
  transportation_logistics: 'teal',
  logistics: 'teal',
  information: 'blue',
  information_services: 'blue',
  software: 'violet',
  software_it: 'violet',
  it_services: 'violet',
  cloud_data_web: 'sky',
  telecommunications: 'cyan',
  finance_insurance: 'emerald',
  real_estate_rental: 'lime',
  professional_services: 'purple',
  engineering: 'blue',
  engineering_architecture: 'blue',
  management: 'rose',
  management_consulting: 'rose',
  consulting: 'rose',
  administrative_support: 'gray',
  education: 'yellow',
  education_training: 'yellow',
  healthcare: 'red',
  healthcare_social_assistance: 'red',
  medical_equipment: 'red',
  medical_manufacturing: 'red',
  pharmaceuticals: 'red',
  arts_entertainment_recreation: 'pink',
  accommodation_food_services: 'amber',
  other_services: 'stone',
  public_administration: 'slate',
  computer_hardware: 'indigo',
  communications_equipment: 'cyan',
  electronics_instruments: 'fuchsia',
  electronics_semiconductors: 'fuchsia',
  aerospace: 'sky',
  technology_wholesale: 'violet',
  healthcare_wholesale: 'red',
  industrial_equipment: 'orange',
  research_development: 'purple',
  other: 'gray',
};
const DISMISSED_STORAGE_KEY = 'dismissedDashboardOpportunities';
const RECENTLY_VIEWED_STORAGE_KEY = 'recentlyViewedContractsByWorkspace';
const MAX_RECENTLY_VIEWED = 8;

const CONTRACTS_PER_PAGE = 10;

const WORKSPACE_CONFIG = {
  dashboard: {
    pageTitle: 'Dashboard',
    searchPlaceholder: 'Search opportunities...',
    sectionTitle: 'Explore Contracts',
    sectionHelperText: 'Filter live opportunities by agency, partner, status, NAICS code, and search terms.',
    recentTitle: 'Recently Visited',
    emptyMessage: 'No opportunities match the selected filters.',
    loadingMessage: 'Loading opportunities from the backend...',
    activeNav: 'dashboard',
    showSummary: true,
    showSync: true,
    showRecentVisits: true,
    allowDismiss: true,
    dismissLabel: 'Not Interested',
  },
  matchmaking: {
    pageTitle: 'AI Matchmaking',
    searchPlaceholder: 'Search matched contracts...',
    sectionTitle: 'Matched Contracts',
    sectionHelperText: 'Get matched with the top capability statements for you based on your profile, NAICS codes, and uploaded materials.',
    recentTitle: 'Closest Matches',
    emptyMessage: 'No matched contracts fit the current filters. Try clearing a filter or broadening your search.',
    loadingMessage: 'Finding profile-based matches for your account...',
    activeNav: 'matchmaking',
    showSummary: false,
    showSync: false,
    showRecentVisits: false,
    overviewTitle: 'Profile-Based Matches',
    overviewText: 'Get matched with the best-fit contracts for your business using your profile and capability statement details.',
    overviewMetricLabel: 'Matched',
    allowDismiss: true,
    dismissLabel: 'Not Interested',
  },
  myContracts: {
    pageTitle: 'My Contracts',
    searchPlaceholder: 'Search your active contracts...',
    sectionTitle: 'Active Tracking',
    sectionHelperText: 'This board shows contracts where progress moved beyond Not tracked or workflow moved beyond Not Started.',
    recentTitle: 'Recently Tracked',
    emptyMessage: 'No tracked contracts fit the current filters.',
    loadingMessage: 'Loading tracked contracts...',
    activeNav: 'my-contracts',
    showSummary: false,
    showSync: false,
    showRecentVisits: false,
    overviewTitle: 'Current Workboard',
    overviewText: 'Contracts land here when you start actively working them, whether that means progress labels or workflow steps.',
    overviewMetricLabel: 'Active',
    allowDismiss: false,
    dismissLabel: '',
  },
};

function getNaicsCategoryClass(category) {
  const normalizedCategory = String(category || 'other').trim().toLowerCase();
  const colorName = NAICS_CATEGORY_COLORS[normalizedCategory] || 'gray';
  return `info-pill naics-tag naics-tag-${colorName}`;
}

function getListingStatusClass(status) {
  const normalizedStatus = String(status || 'unknown').trim().toLowerCase();
  const colorName = LISTING_STATUS_COLORS[normalizedStatus] || 'gray';
  return `info-pill status-color-${colorName}`;
}

function getProgressStatusClass(status) {
  const normalizedStatus = String(status || 'NONE').trim().toUpperCase();
  const colorName = PROGRESS_STATUS_COLORS[normalizedStatus] || 'gray';
  return `status-tag status-color-${colorName}`;
}

function getWorkflowStatusClass(status) {
  const normalizedStatus = String(status || 'NOT_STARTED').trim().toUpperCase();
  const colorName = WORKFLOW_STATUS_COLORS[normalizedStatus] || 'gray';
  return `status-tag status-color-${colorName}`;
}

function getRelationshipLabelClass(label) {
  const normalizedLabel = String(label || 'UNASSIGNED').trim().toUpperCase();
  const colorName = RELATIONSHIP_LABEL_COLORS[normalizedLabel] || 'gray';
  return `status-tag status-color-${colorName}`;
}

function formatNaicsCategory(category) {
  return String(category || 'Other')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatProgressStatus(status) {
  const normalizedStatus = String(status || 'NONE').trim().toUpperCase();
  return PROGRESS_STATUS_LABELS[normalizedStatus] || normalizedStatus;
}

function formatWorkflowStatus(status) {
  const normalizedStatus = String(status || 'NOT_STARTED').trim().toUpperCase();
  return WORKFLOW_STATUS_LABELS[normalizedStatus] || normalizedStatus.replace(/_/g, ' ');
}

function formatBreakdownLabel(key) {
  return String(key || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatRelationshipLabel(label) {
  const normalizedLabel = String(label || 'UNASSIGNED').trim().toUpperCase();
  return RELATIONSHIP_LABELS[normalizedLabel] || normalizedLabel.replace(/_/g, ' ');
}

function formatLastSynced() {
  return new Date().toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function readDismissedOpportunities() {
  try {
    const storedValue = window.localStorage.getItem(DISMISSED_STORAGE_KEY);
    const parsedValue = JSON.parse(storedValue || '[]');
    return Array.isArray(parsedValue) ? parsedValue : [];
  } catch {
    return [];
  }
}

function writeDismissedOpportunities(ids) {
  window.localStorage.setItem(DISMISSED_STORAGE_KEY, JSON.stringify(ids));
}

function readRecentlyViewedContracts(workspaceType) {
  try {
    const storedValue = window.localStorage.getItem(RECENTLY_VIEWED_STORAGE_KEY);
    const parsedValue = JSON.parse(storedValue || '{}');
    const workspaceIds = parsedValue?.[workspaceType];
    return Array.isArray(workspaceIds) ? workspaceIds : [];
  } catch {
    return [];
  }
}

function writeRecentlyViewedContracts(workspaceType, ids) {
  try {
    const storedValue = window.localStorage.getItem(RECENTLY_VIEWED_STORAGE_KEY);
    const parsedValue = JSON.parse(storedValue || '{}');
    parsedValue[workspaceType] = ids;
    window.localStorage.setItem(RECENTLY_VIEWED_STORAGE_KEY, JSON.stringify(parsedValue));
  } catch {
    window.localStorage.setItem(
      RECENTLY_VIEWED_STORAGE_KEY,
      JSON.stringify({ [workspaceType]: ids }),
    );
  }
}

async function syncSamOpportunities(limit = 10) {
  const response = await fetch('http://127.0.0.1:8000/api/sam/sync/', {
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

async function fetchOpportunities(signal, token, { matchUser = false } = {}) {
  const headers = token ? { Authorization: `Token ${token}` } : {};
  const url = new URL(OPPORTUNITIES_API_URL);

  if (matchUser) {
    url.searchParams.set('match_user', 'true');
  }

  const response = await fetch(url, { signal, headers });

  let data = [];
  try {
    data = await response.json();
  } catch {
    data = [];
  }

  if (!response.ok) {
    throw new Error(data.detail || 'Failed to load opportunities.');
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

function isTrackedContract(opportunity) {
  return (
    (opportunity.contract_progress && opportunity.contract_progress !== 'NONE')
    || (opportunity.workflow_status && opportunity.workflow_status !== 'NOT_STARTED')
    || (opportunity.relationship_label && opportunity.relationship_label !== 'UNASSIGNED')
  );
}

function ContractsDisplayPage({ workspaceType }) {
  const config = WORKSPACE_CONFIG[workspaceType] || WORKSPACE_CONFIG.dashboard;
  const navigate = useNavigate();
  const location = useLocation();
  const recentSectionRef = useRef(null);
  const restoreWorkspaceState = (
    location.state?.restoreWorkspace?.pathname === location.pathname
      ? location.state.restoreWorkspace
      : null
  );
  const hasRestoredPosition = useRef(false);
  const [hoveredId, setHoveredId] = useState(null);
  const [allOpportunities, setAllOpportunities] = useState([]);
  const [searchTerm, setSearchTerm] = useState(restoreWorkspaceState?.searchTerm || '');
  const [selectedNaics, setSelectedNaics] = useState(restoreWorkspaceState?.selectedNaics || '');
  const [selectedAgency, setSelectedAgency] = useState(restoreWorkspaceState?.selectedAgency || '');
  const [selectedPartner, setSelectedPartner] = useState(restoreWorkspaceState?.selectedPartner || '');
  const [selectedStatus, setSelectedStatus] = useState(restoreWorkspaceState?.selectedStatus || '');
  const [dismissedOpportunityIds, setDismissedOpportunityIds] = useState(() => readDismissedOpportunities());
  const [recentlyViewedIds, setRecentlyViewedIds] = useState(() => readRecentlyViewedContracts(workspaceType));
  const [currentPage, setCurrentPage] = useState(1);
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
  const unreadCount = useNotificationSummary();

  useEffect(() => {
    const controller = new AbortController();

    const loadOpportunities = async () => {
      setLoading(true);
      setError('');

      try {
        const data = await fetchOpportunities(
          controller.signal,
          token,
          { matchUser: workspaceType === 'matchmaking' }
        );
        setAllOpportunities(data);

        if (config.showSummary) {
          const summary = await fetchProgressSummary(controller.signal, token);
          setProgressSummary(summary);
        }

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
  }, [config.showSummary, token, workspaceType]);

  useEffect(() => {
    writeDismissedOpportunities(dismissedOpportunityIds);
  }, [dismissedOpportunityIds]);

  useEffect(() => {
    writeRecentlyViewedContracts(workspaceType, recentlyViewedIds);
  }, [recentlyViewedIds, workspaceType]);

  const workspaceOpportunities = useMemo(() => {
    const visibleOpportunities = config.allowDismiss
      ? allOpportunities.filter((opportunity) => !dismissedOpportunityIds.includes(opportunity.id))
      : allOpportunities;

    if (workspaceType === 'myContracts') {
      return visibleOpportunities.filter(isTrackedContract);
    }

    return visibleOpportunities;
  }, [allOpportunities, config.allowDismiss, dismissedOpportunityIds, workspaceType]);

  const agencyOptions = useMemo(() => Array.from(
    new Set(
      workspaceOpportunities
        .map((opportunity) => opportunity.agency)
        .filter(Boolean)
    )
  ).sort((left, right) => left.localeCompare(right)), [workspaceOpportunities]);

  const partnerOptions = useMemo(() => Array.from(
    new Set(
      workspaceOpportunities
        .map((opportunity) => opportunity.partner)
        .filter(Boolean)
    )
  ).sort((left, right) => left.localeCompare(right)), [workspaceOpportunities]);

  const naicsOptions = useMemo(() => Array.from(
    new Set(
      workspaceOpportunities
        .map((opportunity) => opportunity.naics_code)
        .filter(Boolean)
    )
  ).sort(), [workspaceOpportunities]);

  const statusOptions = useMemo(() => Array.from(
    new Set(
      workspaceOpportunities
        .map((opportunity) => opportunity.status)
        .filter(Boolean)
    )
  ).sort((left, right) => left.localeCompare(right)), [workspaceOpportunities]);

  const filteredOpportunities = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const normalizedAgency = selectedAgency.trim().toLowerCase();
    const normalizedPartner = selectedPartner.trim().toLowerCase();
    const normalizedStatus = selectedStatus.trim().toLowerCase();

    return workspaceOpportunities.filter((opportunity) => {
      const searchableText = [
        opportunity.title,
        opportunity.agency,
        opportunity.description,
        opportunity.partner,
        opportunity.status,
        opportunity.relationship_label,
        opportunity.naics_code,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      const opportunityAgency = String(opportunity.agency || '').trim().toLowerCase();
      const opportunityPartner = String(opportunity.partner || '').trim().toLowerCase();
      const opportunityStatus = String(opportunity.status || '').trim().toLowerCase();
      const opportunityNaics = String(opportunity.naics_code || '').trim();

      const matchesSearch = !normalizedSearch || searchableText.includes(normalizedSearch);
      const matchesAgency = !normalizedAgency || opportunityAgency === normalizedAgency;
      const matchesPartner = !normalizedPartner || opportunityPartner === normalizedPartner;
      const matchesStatus = !normalizedStatus || opportunityStatus === normalizedStatus;
      const matchesNaics = !selectedNaics || opportunityNaics === selectedNaics;

      return matchesSearch && matchesAgency && matchesPartner && matchesStatus && matchesNaics;
    });
  }, [workspaceOpportunities, searchTerm, selectedAgency, selectedPartner, selectedStatus, selectedNaics]);

  const totalPages = Math.max(1, Math.ceil(filteredOpportunities.length / CONTRACTS_PER_PAGE));

  const paginatedOpportunities = useMemo(() => {
    const startIndex = (currentPage - 1) * CONTRACTS_PER_PAGE;
    return filteredOpportunities.slice(startIndex, startIndex + CONTRACTS_PER_PAGE);
  }, [currentPage, filteredOpportunities]);

  const recentOpportunities = useMemo(() => {
    if (!recentlyViewedIds.length) {
      return [];
    }

    const opportunityMap = new Map(workspaceOpportunities.map((opportunity) => [opportunity.id, opportunity]));

    return recentlyViewedIds
      .map((opportunityId) => opportunityMap.get(opportunityId))
      .filter(Boolean);
  }, [recentlyViewedIds, workspaceOpportunities]);

  const bottomSectionOpportunities = useMemo(() => (
    config.showRecentVisits
      ? recentOpportunities
      : filteredOpportunities.slice(0, 3)
  ), [config.showRecentVisits, filteredOpportunities, recentOpportunities]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, selectedNaics, selectedAgency, selectedPartner, selectedStatus, workspaceType]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  useEffect(() => {
    if (loading || !restoreWorkspaceState?.contractId || hasRestoredPosition.current) {
      return;
    }

    const matchingIndex = filteredOpportunities.findIndex(
      (opportunity) => opportunity.id === restoreWorkspaceState.contractId,
    );

    if (matchingIndex >= 0) {
      const targetPage = Math.floor(matchingIndex / CONTRACTS_PER_PAGE) + 1;
      if (targetPage !== currentPage) {
        setCurrentPage(targetPage);
      }
    }
  }, [currentPage, filteredOpportunities, loading, restoreWorkspaceState]);

  useEffect(() => {
    if (loading || hasRestoredPosition.current || !restoreWorkspaceState) {
      return;
    }

    hasRestoredPosition.current = true;

    window.requestAnimationFrame(() => {
      const contractCard = document.querySelector(
        `[data-contract-id="${restoreWorkspaceState.contractId}"]`
      );

      if (contractCard) {
        contractCard.scrollIntoView({ block: 'center' });
        return;
      }

      if (Number.isFinite(restoreWorkspaceState.scrollY)) {
        window.scrollTo({ top: restoreWorkspaceState.scrollY });
      }
    });
  }, [loading, restoreWorkspaceState]);

  const handleViewDetails = (opportunityId) => {
    setRecentlyViewedIds((currentIds) => [
      opportunityId,
      ...currentIds.filter((existingId) => existingId !== opportunityId),
    ].slice(0, MAX_RECENTLY_VIEWED));

    navigate(`/contracts/${opportunityId}`, {
      state: {
        workspaceReturn: {
          pathname: location.pathname,
          pageTitle: config.pageTitle,
          contractId: opportunityId,
          scrollY: window.scrollY,
          searchTerm,
          selectedNaics,
          selectedAgency,
          selectedPartner,
          selectedStatus,
        },
      },
    });
  };

  const handleJumpToRecent = () => {
    recentSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleSyncContracts = async () => {
    if (isSyncing) {
      return;
    }

    setIsSyncing(true);
    setError('');

    try {
      await syncSamOpportunities(10);

      const summaryPromise = config.showSummary
        ? fetchProgressSummary(undefined, token)
        : Promise.resolve(progressSummary);
      const [catalogData, summaryData] = await Promise.all([
        fetchOpportunities(undefined, token, { matchUser: workspaceType === 'matchmaking' }),
        summaryPromise,
      ]);

      setAllOpportunities(catalogData);
      if (config.showSummary) {
        setProgressSummary(summaryData);
      }
      setLastSynced(formatLastSynced());
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

  const handleDismissOpportunity = (opportunityId) => {
    const confirmed = window.confirm(
      'Are you sure you want to mark this contract as not interested and remove it from this page? You cannot undo this.'
    );

    if (!confirmed) {
      return;
    }

    setDismissedOpportunityIds((currentIds) => (
      currentIds.includes(opportunityId)
        ? currentIds
        : [...currentIds, opportunityId]
    ));
  };

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <h2 className="sidebar-title">AI Matchmaking Tool</h2>

        <nav className="sidebar-nav">
          <button
            className={`sidebar-link ${config.activeNav === 'dashboard' ? 'active' : ''}`}
            onClick={() => navigate('/dashboard')}
          >
            Dashboard
          </button>
          <button
            className={`sidebar-link ${config.activeNav === 'matchmaking' ? 'active' : ''}`}
            onClick={() => navigate('/ai-matchmaking')}
          >
            AI Matchmaking
          </button>
          <button
            className={`sidebar-link ${config.activeNav === 'my-contracts' ? 'active' : ''}`}
            onClick={() => navigate('/my-contracts')}
          >
            My Contracts
          </button>
          <button className="sidebar-link" onClick={() => navigate('/profile')}>
            Profile
          </button>
          <button className="sidebar-link" onClick={() => navigate('/notifications')}>
            <span className="sidebar-link-content">
              <span>Notifications</span>
              {unreadCount > 0 && <span className="nav-notification-badge">{unreadCount}</span>}
            </span>
          </button>
        </nav>
      </aside>

      <div className="dashboard-main">
        <header className="dashboard-topbar">
          <div className="dashboard-inner">
            <div className="topbar-icons">
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
            <h1 className="page-title">{config.pageTitle}</h1>

            <div className="workspace-quick-actions">
              <button
                className="jump-section-button"
                type="button"
                onClick={handleJumpToRecent}
              >
                Jump to {config.recentTitle}
              </button>
            </div>

            {config.showSummary && (
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
            )}

            {config.showSync && (
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
            )}

            {config.overviewTitle && (
              <section className="section workspace-overview-card">
                <div>
                  <h2 className="section-title">{config.overviewTitle}</h2>
                  <p className="section-helper-text">{config.overviewText}</p>
                </div>
                <div className="workspace-overview-metric">
                  <span>{config.overviewMetricLabel}</span>
                  <strong>{workspaceOpportunities.length}</strong>
                </div>
              </section>
            )}

            <section className="section">
              <div className="section-heading-row">
                <div>
                  <h2 className="section-title">{config.sectionTitle}</h2>
                  <p className="section-helper-text">{config.sectionHelperText}</p>
                </div>
              </div>
              <div className="filters-grid">
                <div className="filter-group filter-group-search">
                  <label htmlFor="contractsSearch" className="filter-label">
                    Search
                  </label>
                  <input
                    id="contractsSearch"
                    type="text"
                    placeholder={config.searchPlaceholder}
                    className="search-bar contracts-search-bar"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                  />
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
                  <label htmlFor="partnerFilter" className="filter-label">
                    Partner
                  </label>
                  <select
                    id="partnerFilter"
                    className="partner-filter"
                    value={selectedPartner}
                    onChange={(event) => setSelectedPartner(event.target.value)}
                  >
                    <option value="">All Partners</option>
                    {partnerOptions.map((partner) => (
                      <option key={partner} value={partner}>
                        {partner}
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
                    {statusOptions.map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {loading ? (
                <div className="state-card">{config.loadingMessage}</div>
              ) : error ? (
                <div className="state-card state-card-error">{error}</div>
              ) : filteredOpportunities.length === 0 ? (
                <div className="state-card">{config.emptyMessage}</div>
              ) : (
                <>
                  <div className="contract-list">
                    {paginatedOpportunities.map((opportunity) => {
                      const hasProgressTag = opportunity.contract_progress && opportunity.contract_progress !== 'NONE';
                      const hasWorkflowTag = opportunity.workflow_status && opportunity.workflow_status !== 'NOT_STARTED';
                      const hasRelationshipTag = opportunity.relationship_label && opportunity.relationship_label !== 'UNASSIGNED';
                      const showMatchDetails = workspaceType === 'matchmaking' && Number.isFinite(opportunity.match_percentage);
                      const strongestAlignment = Array.isArray(opportunity.strongest_alignment)
                        ? opportunity.strongest_alignment.filter(Boolean)
                        : [];
                      const weakAlignment = Array.isArray(opportunity.weak_alignment)
                        ? opportunity.weak_alignment.filter(Boolean)
                        : [];
                      const matchBreakdown = opportunity.match_breakdown && typeof opportunity.match_breakdown === 'object'
                        ? opportunity.match_breakdown
                        : null;

                      return (
                        <div
                          key={opportunity.id}
                          className="contract-card"
                          data-contract-id={opportunity.id}
                        >
                          <div className={`card-heading-row ${(hasProgressTag || hasWorkflowTag || hasRelationshipTag) ? 'card-heading-row-with-tags' : 'card-heading-row-no-tags'}`}>
                            <div className="card-heading-copy">
                              <div className="title-row">
                                <h3>{opportunity.title}</h3>
                                {showMatchDetails && (
                                  <span className="match-percentage-badge">
                                    {opportunity.match_percentage}% match
                                  </span>
                                )}
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
                              {showMatchDetails && (
                                <div className="match-insights">
                                  {strongestAlignment.length > 0 && (
                                    <div className="match-chip-row">
                                      {strongestAlignment.map((label) => (
                                        <span className="alignment-chip alignment-chip-strong" key={label}>
                                          {label}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                  {weakAlignment.length > 0 && (
                                    <div className="match-chip-row match-chip-row-weak">
                                      {weakAlignment.map((label) => (
                                        <span className="alignment-chip alignment-chip-weak" key={label}>
                                          {label}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                  {matchBreakdown && (
                                    <div className="match-breakdown-row" aria-label="Match breakdown">
                                      {Object.entries(matchBreakdown).map(([key, value]) => (
                                        <span className="match-breakdown-item" key={key}>
                                          <span>{formatBreakdownLabel(key)}</span>
                                          <strong>{value}</strong>
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                              {(hasProgressTag || hasWorkflowTag || hasRelationshipTag) && (
                                <div className="tracking-tag-row">
                                  {hasProgressTag && (
                                    <span className={getProgressStatusClass(opportunity.contract_progress)}>
                                      {formatProgressStatus(opportunity.contract_progress)}
                                    </span>
                                  )}
                                  {hasWorkflowTag && (
                                    <span className={getWorkflowStatusClass(opportunity.workflow_status)}>
                                      {formatWorkflowStatus(opportunity.workflow_status)}
                                    </span>
                                  )}
                                  {hasRelationshipTag && (
                                    <span className={getRelationshipLabelClass(opportunity.relationship_label)}>
                                      {formatRelationshipLabel(opportunity.relationship_label)}
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                            <div className="card-action-row">
                              <button
                                className="note-action-button"
                                type="button"
                                onClick={() => handleViewDetails(opportunity.id)}
                              >
                                View Details
                              </button>
                              {config.allowDismiss && (
                                <button
                                  className="note-secondary-button"
                                  type="button"
                                  onClick={() => handleDismissOpportunity(opportunity.id)}
                                >
                                  {config.dismissLabel}
                                </button>
                              )}
                            </div>
                          </div>

                          <p className="contract-description-preview">
                            {opportunity.description || 'No description available.'}
                          </p>

                          <p>
                            <strong>Agency:</strong>{' '}
                            <span className="info-pill agency-pill">{opportunity.agency || 'Not provided'}</span>
                          </p>
                          <p>
                            <strong>Partner:</strong>{' '}
                            <span className="info-pill partner-pill">{opportunity.partner || 'Not provided'}</span>
                          </p>
                          <p>
                            <strong>NAICS Code:</strong>{' '}
                            <span
                              className={getNaicsCategoryClass(opportunity.naics_category)}
                              title={formatNaicsCategory(opportunity.naics_category)}
                            >
                              {opportunity.naics_code}
                            </span>
                          </p>
                          <p>
                            <strong>Contract Status:</strong>{' '}
                            <span className={getListingStatusClass(opportunity.status)}>
                              {opportunity.status || 'Unknown'}
                            </span>
                          </p>
                        </div>
                      );
                    })}
                  </div>
                  <div className="pagination-row">
                    <p className="pagination-summary">
                      Showing {Math.min((currentPage - 1) * CONTRACTS_PER_PAGE + 1, filteredOpportunities.length)}-
                      {Math.min(currentPage * CONTRACTS_PER_PAGE, filteredOpportunities.length)} of {filteredOpportunities.length}
                    </p>
                    <div className="pagination-controls">
                      <button
                        className="pagination-button"
                        type="button"
                        onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                        disabled={currentPage === 1}
                      >
                        Previous
                      </button>
                      <span className="pagination-page-indicator">
                        Page {currentPage} of {totalPages}
                      </span>
                      <button
                        className="pagination-button"
                        type="button"
                        onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                        disabled={currentPage === totalPages}
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </>
              )}
            </section>

            <section className="section" ref={recentSectionRef}>
              {config.showRecentVisits ? (
                <div className="section-heading-row recent-section-heading-row">
                  <div>
                    <h2 className="section-title">{config.recentTitle}</h2>
                    <p className="section-helper-text">
                      Contracts you opened with View Details show up here so you can get back to them faster.
                    </p>
                  </div>
                  <button
                    className="jump-section-button jump-section-button-secondary"
                    type="button"
                    onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                  >
                    Back to Top
                  </button>
                </div>
              ) : (
                <div className="section-heading-row recent-section-heading-row">
                  <div>
                    <h2 className="section-title">{config.recentTitle}</h2>
                  </div>
                  <button
                    className="jump-section-button jump-section-button-secondary"
                    type="button"
                    onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                  >
                    Back to Top
                  </button>
                </div>
              )}
              {bottomSectionOpportunities.length === 0 ? (
                <div className="state-card">
                  {config.showRecentVisits
                    ? 'No recently visited contracts yet.'
                    : 'No opportunities available for the current filters.'}
                </div>
              ) : (
                <div className="history-table-wrapper">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Title</th>
                        <th>Agency</th>
                        <th>NAICS</th>
                        {config.showRecentVisits && <th>Action</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {bottomSectionOpportunities.map((opportunity) => (
                        <tr key={opportunity.id}>
                          <td>{opportunity.title}</td>
                          <td>{opportunity.agency || 'Not provided'}</td>
                          <td>
                            <span
                              className={getNaicsCategoryClass(opportunity.naics_category)}
                              title={formatNaicsCategory(opportunity.naics_category)}
                            >
                              {opportunity.naics_code || 'Not provided'}
                            </span>
                          </td>
                          {config.showRecentVisits && (
                            <td>
                              <button
                                className="history-action-button"
                                type="button"
                                onClick={() => handleViewDetails(opportunity.id)}
                              >
                                View Details
                              </button>
                            </td>
                          )}
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

export default ContractsDisplayPage;
