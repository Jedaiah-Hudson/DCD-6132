import './NotificationsPage.css';
import { useNavigate } from 'react-router-dom';

function NotificationsPage() {
  const navigate = useNavigate();
  const notifications = [
    'New contract opportunity added.',
    'Capability profile updated successfully.',
    'A saved contract deadline is approaching.',
  ];

  return (
    <div className="notifications-layout">
      <aside className="notifications-sidebar">
        <h2 className="notifications-sidebar-title">AI Matchmaking Tool</h2>

        <nav className="notifications-sidebar-nav">
            <button className="notifications-sidebar-link" onClick={() => navigate('/dashboard')}>
                Dashboard
            </button>
            <button className="notifications-sidebar-link" onClick={() => navigate('/dashboard')}>
                AI Matchmaking
            </button>
            <button className="notifications-sidebar-link" onClick={() => navigate('/profile')}>
                Profile
            </button>
            <button className="notifications-sidebar-link active" onClick={() => navigate('/notifications')}>
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

        <main className="notifications-content">
          <div className="notifications-inner">
            <h1 className="notifications-page-title">Notifications</h1>

            <section className="notifications-section-card">
              <h2 className="notifications-section-title">Recent Notifications</h2>

              <div className="notifications-list">
                {notifications.map((item, index) => (
                  <div key={index} className="notification-card">
                    {item}
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