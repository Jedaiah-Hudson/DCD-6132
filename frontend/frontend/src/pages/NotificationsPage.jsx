import './NotificationsPage.css';
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

function NotificationsPage() {
  const navigate = useNavigate();

  const notifications = [
    {
      id: 1,
      title: 'Cybersecurity Infrastructure Enhancement',
      agency: 'Department of Defense',
      source: 'Email',
      dueDate: 'April 9, 2026',
      urgency: 'High',
      message: 'Deadline is very close. Review and prioritize this contract opportunity immediately.',
    },
    {
      id: 2,
      title: 'Medical Equipment Manufacturing Contract',
      agency: 'Department of Health & Human Services',
      source: 'Procurement Portal',
      dueDate: 'April 14, 2026',
      urgency: 'Medium',
      message: 'New contract opportunity added and ready for review.',
    },
    {
      id: 3,
      title: 'Healthcare IT System Implementation',
      agency: 'Veterans Affairs',
      source: 'Email',
      dueDate: 'April 18, 2026',
      urgency: 'Medium',
      message: 'This opportunity should be reviewed soon to avoid falling behind.',
    },
    {
      id: 4,
      title: 'Industrial Equipment Maintenance Services',
      agency: 'General Services Administration',
      source: 'Procurement Portal',
      dueDate: 'April 24, 2026',
      urgency: 'Low',
      message: 'This contract has more time before the deadline but should remain on the board.',
    },
  ];

  const priorityOrder = {
    High: 0,
    Medium: 1,
    Low: 2,
  };

  const sortedNotifications = useMemo(() => {
    return [...notifications].sort(
      (a, b) => priorityOrder[a.urgency] - priorityOrder[b.urgency]
    );
  }, []);

  const getUrgencyClassName = (urgency) => {
    if (urgency === 'High') {
      return 'urgency-badge urgency-high';
    }

    if (urgency === 'Medium') {
      return 'urgency-badge urgency-medium';
    }

    return 'urgency-badge urgency-low';
  };

  return (
    <div className="notifications-layout">
      <aside className="notifications-sidebar">
        <h2 className="notifications-sidebar-title">AI Matchmaking Tool</h2>

        <nav className="notifications-sidebar-nav">
          <button className="notifications-sidebar-link" onClick={() => navigate('/dashboard')}>
            Dashboard
          </button>
          <button className="notifications-sidebar-link" onClick={() => navigate('/ai-matchmaking')}>
            AI Matchmaking
          </button>
          <button className="notifications-sidebar-link" onClick={() => navigate('/my-contracts')}>
            My Contracts
          </button>
          <button className="notifications-sidebar-link" onClick={() => navigate('/profile')}>
            Profile
          </button>
          <button
            className="notifications-sidebar-link active"
            onClick={() => navigate('/notifications')}
          >
            Notifications
          </button>
        </nav>
      </aside>

      <div className="notifications-main">
        <header className="notifications-topbar">
          <div className="notifications-inner">
            <input
              type="text"
              placeholder="Search contracts..."
              className="notifications-search-bar"
            />
            <div className="notifications-topbar-icons">
              <span
                className="profile-icon-circle"
                onClick={() => navigate('/notifications')}
                style={{ cursor: 'pointer' }}
                title="Notifications"
              >
                {sortedNotifications.length}
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

        <main className="notifications-content">
          <div className="notifications-inner">
            <h1 className="notifications-page-title">Notifications</h1>
            <p className="notifications-subtitle">
              Time-prioritized contract opportunities are shown below in order of urgency.
            </p>

            <section className="notifications-section-card">
              <div className="notifications-section-header">
                <div>
                  <h2 className="notifications-section-title">Priority Notification Board</h2>
                  <p className="notifications-helper-text">
                    Contracts are sorted by urgency so the most time-sensitive items appear first.
                  </p>
                </div>
              </div>

              <div className="notifications-list">
                {sortedNotifications.map((item) => (
                  <div key={item.id} className="notification-card">
                    <div className="notification-card-header">
                      <div>
                        <h3 className="notification-title">{item.title}</h3>
                        <p className="notification-agency">{item.agency}</p>
                      </div>

                      <span className={getUrgencyClassName(item.urgency)}>
                        {item.urgency} Priority
                      </span>
                    </div>

                    <div className="notification-meta-row">
                      <span className="notification-meta-item">
                        <strong>Source:</strong> {item.source}
                      </span>
                      <span className="notification-meta-item">
                        <strong>Deadline:</strong> {item.dueDate}
                      </span>
                    </div>

                    <div className="notification-message-box">
                      {item.message}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}

export default NotificationsPage;
