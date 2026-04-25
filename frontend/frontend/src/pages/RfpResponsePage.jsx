import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import './DashboardPage.css';
import './ContractDetailPage.css';
import './RfpResponsePage.css';
import useNotificationSummary from '../hooks/useNotificationSummary';

const API_BASE_URL = 'http://127.0.0.1:8000';

function RfpResponsePage() {
  const { contractId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const workspaceReturn = location.state?.workspaceReturn;
  const token = localStorage.getItem('token');
  const unreadCount = useNotificationSummary();

  const [contractTitle, setContractTitle] = useState('RFP Response');
  const [generatedText, setGeneratedText] = useState('');
  const [draftText, setDraftText] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copyMessage, setCopyMessage] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    const loadDraft = async () => {
      setLoading(true);
      setError('');
      setCopyMessage('');

      try {
        const response = await fetch(`${API_BASE_URL}/generate-draft/`, {
          method: 'POST',
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Token ${token}` } : {}),
          },
          body: JSON.stringify({ contract_id: Number(contractId) }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || data.detail || 'Failed to generate RFP response.');
        }

        const nextText = data.generated_text || '';
        setContractTitle(data.contract_title || 'RFP Response');
        setGeneratedText(nextText);
        setDraftText(nextText);
      } catch (loadError) {
        if (loadError.name !== 'AbortError') {
          setError(loadError.message || 'Could not generate the RFP response.');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    loadDraft();

    return () => controller.abort();
  }, [contractId, token]);

  useEffect(() => {
    if (!copyMessage) return undefined;
    const timeoutId = window.setTimeout(() => setCopyMessage(''), 2500);
    return () => window.clearTimeout(timeoutId);
  }, [copyMessage]);

  const handleBack = () => {
    navigate(`/contracts/${contractId}`, {
      state: workspaceReturn ? { workspaceReturn } : undefined,
    });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(draftText);
      setCopyMessage('Copied to clipboard.');
    } catch (_error) {
      setCopyMessage('Copy failed.');
    }
  };

  const mailtoHref = useMemo(() => {
    const subject = encodeURIComponent(`${contractTitle} RFP Draft`);
    const body = encodeURIComponent(draftText);
    return `mailto:?subject=${subject}&body=${body}`;
  }, [contractTitle, draftText]);

  const pageTitle = workspaceReturn?.pageTitle
    ? `${workspaceReturn.pageTitle} / RFP Draft`
    : 'RFP Draft';

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
            <button className="notes-cancel-button" onClick={handleBack}>
              Back to Contract
            </button>
            <div className="topbar-icons">
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
            <p className="rfp-page-kicker">{pageTitle}</p>
            <h1 className="page-title">{contractTitle}</h1>

            <section className="section detail-section rfp-page-section">
              <div className="rfp-page-header">
                <div>
                  <h2 className="section-title rfp-page-title">Generated RFP draft</h2>
                  <p className="section-helper-text rfp-helper-text">
                    Review the generated proposal draft, then copy, edit, or open it in email.
                  </p>
                </div>
                <div className="rfp-toolbar">
                  <a className="rfp-action-button secondary" href={mailtoHref}>
                    Mail To
                  </a>
                  <button className="rfp-action-button secondary" onClick={handleCopy} disabled={!draftText}>
                    Copy
                  </button>
                  <button
                    className={`rfp-action-button ${isEditing ? 'primary' : 'secondary'}`}
                    onClick={() => setIsEditing((current) => !current)}
                    disabled={loading || !!error}
                  >
                    {isEditing ? 'Done Editing' : 'Edit'}
                  </button>
                </div>
              </div>

              {loading ? (
                <div className="state-card">Generating RFP draft...</div>
              ) : error ? (
                <div className="state-card state-card-error">{error}</div>
              ) : (
                <>
                  {copyMessage && <div className="state-card detail-success-message">{copyMessage}</div>}
                  {isEditing ? (
                    <textarea
                      className="rfp-editor"
                      value={draftText}
                      onChange={(event) => setDraftText(event.target.value)}
                      placeholder="The generated RFP response will appear here."
                    />
                  ) : (
                    <div className="rfp-output-card">
                      {draftText.split('\n').map((paragraph, index) => (
                        <p key={`${index}-${paragraph.slice(0, 20)}`}>{paragraph || '\u00A0'}</p>
                      ))}
                    </div>
                  )}
                </>
              )}
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}

export default RfpResponsePage;
