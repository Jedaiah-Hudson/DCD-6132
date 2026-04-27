import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import './DashboardPage.css';
import './RfpGeneratorPage.css';
import useNotificationSummary from '../hooks/useNotificationSummary';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

function RfpGeneratorPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const token = localStorage.getItem('token');
  const unreadCount = useNotificationSummary();
  const initialContractId = location.state?.selectedContractId
    ? String(location.state.selectedContractId)
    : '';

  const [contracts, setContracts] = useState([]);
  const [selectedContractId, setSelectedContractId] = useState(initialContractId);
  const [generatedText, setGeneratedText] = useState('');
  const [contractTitle, setContractTitle] = useState('');
  const [loadingContracts, setLoadingContracts] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [copyMessage, setCopyMessage] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    const loadContracts = async () => {
      setLoadingContracts(true);
      setError('');

      try {
        const response = await fetch(`${API_BASE_URL}/opportunities/`, {
          signal: controller.signal,
          headers: token ? { Authorization: `Token ${token}` } : {},
        });
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Failed to load contracts.');
        }

        setContracts(Array.isArray(data) ? data : []);
      } catch (loadError) {
        if (loadError.name !== 'AbortError') {
          setError(loadError.message || 'Could not load contracts.');
          setContracts([]);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingContracts(false);
        }
      }
    };

    loadContracts();

    return () => controller.abort();
  }, [token]);

  const selectedContract = useMemo(
    () => contracts.find((contract) => String(contract.id) === String(selectedContractId)),
    [contracts, selectedContractId]
  );

  const handleGenerate = async () => {
    if (!selectedContractId) {
      setError('Choose a contract before generating an RFP response.');
      return;
    }

    setGenerating(true);
    setError('');
    setCopyMessage('');
    setGeneratedText('');

    try {
      const response = await fetch(`${API_BASE_URL}/rfp/generate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Token ${token}`,
        },
        body: JSON.stringify({ contract_id: selectedContractId }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Failed to generate the RFP response.');
      }

      setContractTitle(data.contract_title || selectedContract?.title || 'Selected Contract');
      setGeneratedText(data.generated_text || 'No generated text was returned.');
    } catch (generateError) {
      setError(generateError.message || 'Could not generate the RFP response.');
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (!generatedText) {
      return;
    }

    try {
      await navigator.clipboard.writeText(generatedText);
      setCopyMessage('Copied generated response.');
    } catch {
      setCopyMessage('Copy failed. You can still select and copy the text manually.');
    }
  };

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
          <button className="sidebar-link active" onClick={() => navigate('/my-contracts')}>
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
            <button
              className="notes-cancel-button rfp-back-button"
              type="button"
              onClick={() => navigate('/my-contracts')}
            >
              Back to My Contracts
            </button>

            <h1 className="page-title">Generate RFP Response</h1>

            <section className="section rfp-card">
              <div className="section-heading-row">
                <div>
                  <h2 className="section-title">Choose Contract</h2>
                  <p className="section-helper-text">
                    Select a contract by database ID, then generate a draft response using your saved capability profile.
                  </p>
                </div>
              </div>

              {error && <div className="state-card state-card-error rfp-message">{error}</div>}

              <label className="filter-label" htmlFor="rfpContractSelect">
                Contract ID
              </label>
              <select
                id="rfpContractSelect"
                className="partner-filter rfp-contract-select"
                value={selectedContractId}
                onChange={(event) => setSelectedContractId(event.target.value)}
                disabled={loadingContracts}
              >
                <option value="">
                  {loadingContracts ? 'Loading contracts...' : 'Select a contract'}
                </option>
                {contracts.map((contract) => (
                  <option key={contract.id} value={contract.id}>
                    #{contract.id} — {contract.title}
                  </option>
                ))}
              </select>

              {selectedContract && (
                <div className="rfp-selected-contract">
                  <strong>{selectedContract.title}</strong>
                  <span>{selectedContract.agency || 'Agency not provided'}</span>
                  <span>NAICS: {selectedContract.naics_code || 'Not provided'}</span>
                </div>
              )}

              <button
                className="notes-save-button rfp-generate-button"
                type="button"
                onClick={handleGenerate}
                disabled={generating || loadingContracts || !selectedContractId || !token}
              >
                {generating ? 'Generating...' : 'Generate Response'}
              </button>
            </section>

            <section className="section rfp-card">
              <div className="rfp-result-header">
                <div>
                  <h2 className="section-title">Generated Result</h2>
                  <p className="section-helper-text">
                    {contractTitle ? `Draft for ${contractTitle}` : 'The generated text will populate below.'}
                  </p>
                </div>
                <button
                  className="note-secondary-button"
                  type="button"
                  onClick={handleCopy}
                  disabled={!generatedText}
                >
                  Copy Text
                </button>
              </div>

              {copyMessage && <div className="state-card detail-success-message rfp-message">{copyMessage}</div>}

              <textarea
                className="notes-textarea rfp-result-box"
                value={generatedText}
                readOnly
                placeholder="Generated RFP response will appear here after you choose a contract and click Generate Response."
              />
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}

export default RfpGeneratorPage;
