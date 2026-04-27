import './NotificationsPage.css';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const NOTIFICATIONS_API_URL = 'http://127.0.0.1:8000/api/notifications/';
const NOTIFICATIONS_BULK_UPDATE_API_URL = 'http://127.0.0.1:8000/api/notifications/bulk-update/';
const NOTIFICATIONS_PER_PAGE = 10;

function formatDate(value) {
  if (!value) {
    return 'No deadline';
  }

  return new Date(value).toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function NotificationsPage() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    const loadNotifications = async () => {
      if (!token) {
        setNotifications([]);
        setUnreadCount(0);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError('');

      try {
        const response = await fetch(NOTIFICATIONS_API_URL, {
          signal: controller.signal,
          headers: {
            Authorization: `Token ${token}`,
          },
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Failed to load notifications.');
        }

        setNotifications(data.notifications || []);
        setUnreadCount(data.unread_count || 0);
      } catch (loadError) {
        if (loadError.name !== 'AbortError') {
          setError(loadError.message || 'Could not load notifications.');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    loadNotifications();

    return () => controller.abort();
  }, [token]);

  const filteredNotifications = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    return notifications
      .filter((item) => {
        if (!normalizedSearch) {
          return true;
        }

        return [
          item.title,
          item.message,
          item.contract_title,
          item.contract_agency,
          item.notification_type,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(normalizedSearch);
      })
      .sort((left, right) => {
        if (left.is_read !== right.is_read) {
          return left.is_read ? 1 : -1;
        }

        if (left.due_at && right.due_at) {
          return new Date(left.due_at) - new Date(right.due_at);
        }

        return new Date(right.created_at) - new Date(left.created_at);
      });
  }, [notifications, searchTerm]);

  const totalPages = Math.max(1, Math.ceil(filteredNotifications.length / NOTIFICATIONS_PER_PAGE));

  const paginatedNotifications = useMemo(() => {
    const startIndex = (currentPage - 1) * NOTIFICATIONS_PER_PAGE;
    return filteredNotifications.slice(startIndex, startIndex + NOTIFICATIONS_PER_PAGE);
  }, [currentPage, filteredNotifications]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const selectedVisibleCount = paginatedNotifications.filter((item) => selectedIds.includes(item.id)).length;

  const allVisibleSelected = paginatedNotifications.length > 0
    && paginatedNotifications.every((item) => selectedIds.includes(item.id));

  const toggleSelection = (notificationId) => {
    setSelectedIds((currentIds) => (
      currentIds.includes(notificationId)
        ? currentIds.filter((id) => id !== notificationId)
        : [...currentIds, notificationId]
    ));
  };

  const toggleSelectAllVisible = () => {
    if (allVisibleSelected) {
      setSelectedIds((currentIds) => currentIds.filter(
        (id) => !paginatedNotifications.some((item) => item.id === id)
      ));
      return;
    }

    setSelectedIds((currentIds) => Array.from(new Set([
      ...currentIds,
      ...paginatedNotifications.map((item) => item.id),
    ])));
  };

  const handleBulkUpdate = async (markAs, notificationIds = selectedIds) => {
    if (notificationIds.length === 0) {
      return;
    }

    if (markAs === 'delete') {
      const isSingle = notificationIds.length === 1;
      const confirmed = window.confirm(
        isSingle
          ? 'Are you sure you want to remove this notification? You cannot get it back.'
          : 'Are you sure you want to remove these notifications? You cannot get them back.'
      );

      if (!confirmed) {
        return;
      }
    }

    setSaving(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await fetch(NOTIFICATIONS_BULK_UPDATE_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Token ${token}`,
        },
        body: JSON.stringify({
          notification_ids: notificationIds,
          mark_as: markAs,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to update notifications.');
      }

      if (markAs === 'delete') {
        setNotifications((currentNotifications) => currentNotifications.filter(
          (item) => !notificationIds.includes(item.id)
        ));
        setUnreadCount((currentCount) => {
          const deletedUnreadCount = notifications.filter(
            (item) => notificationIds.includes(item.id) && !item.is_read
          ).length;
          return Math.max(0, currentCount - deletedUnreadCount);
        });
        setSelectedIds((currentIds) => currentIds.filter((id) => !notificationIds.includes(id)));
        setSuccessMessage(
          notificationIds.length === 1
            ? 'Notification removed.'
            : 'Selected notifications removed.'
        );
      } else {
        const shouldBeRead = markAs === 'read';
        setNotifications((currentNotifications) => currentNotifications.map((item) => (
          notificationIds.includes(item.id)
            ? { ...item, is_read: shouldBeRead }
            : item
        )));
        setUnreadCount((currentCount) => {
          const selectedUnreadCount = notifications.filter(
            (item) => notificationIds.includes(item.id) && !item.is_read
          ).length;
          const selectedReadCount = notifications.filter(
            (item) => notificationIds.includes(item.id) && item.is_read
          ).length;

          if (shouldBeRead) {
            return Math.max(0, currentCount - selectedUnreadCount);
          }

          return currentCount + selectedReadCount;
        });
        setSuccessMessage(
          markAs === 'read'
            ? 'Selected notifications marked as read.'
            : 'Selected notifications marked as unread.'
        );
        setSelectedIds([]);
      }
    } catch (updateError) {
      setError(updateError.message || 'Could not update notifications.');
    } finally {
      setSaving(false);
    }
  };

  const getSeverityClassName = (severity) => {
    if (severity === 'HIGH') {
      return 'urgency-badge urgency-high';
    }

    if (severity === 'MEDIUM') {
      return 'urgency-badge urgency-medium';
    }

    if (severity === 'LOW') {
      return 'urgency-badge urgency-low';
    }

    return 'urgency-badge urgency-info';
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
            <span className="notifications-sidebar-link-content">
              <span>Notifications</span>
              {unreadCount > 0 && (
                <span className="notifications-nav-notification-badge">{unreadCount}</span>
              )}
            </span>
          </button>
        </nav>
      </aside>

      <div className="notifications-main">
        <header className="notifications-topbar">
          <div className="notifications-inner">
            <input
              type="text"
              placeholder="Search notifications..."
              className="notifications-search-bar"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
            <div className="notifications-topbar-icons">
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
              Stay on top of tracked contracts with deadline, status, and workflow updates.
            </p>

            {error && <div className="notifications-feedback notifications-feedback-error">{error}</div>}
            {successMessage && <div className="notifications-feedback notifications-feedback-success">{successMessage}</div>}

            <section className="notifications-section-card">
              <div className="notifications-section-header">
                <div>
                  <h2 className="notifications-section-title">Contract Alerts</h2>
                  <p className="notifications-helper-text">
                    Notifications appear only for contracts you are actively tracking in My Contracts.
                  </p>
                </div>
              </div>

              <div className="notifications-actions-row">
                <label className="notifications-select-all">
                  <input
                    type="checkbox"
                    checked={allVisibleSelected}
                    onChange={toggleSelectAllVisible}
                    disabled={paginatedNotifications.length === 0}
                  />
                  <span>Select all visible</span>
                </label>

                <div className="notifications-bulk-actions">
                  <button
                    className="notifications-action-button"
                    type="button"
                    onClick={() => handleBulkUpdate('read')}
                    disabled={saving || selectedIds.length === 0}
                  >
                    Mark as read
                  </button>
                  <button
                    className="notifications-action-button notifications-action-button-secondary"
                    type="button"
                    onClick={() => handleBulkUpdate('unread')}
                    disabled={saving || selectedIds.length === 0}
                  >
                    Mark as unread
                  </button>
                  <button
                    className="notifications-action-button notifications-action-button-danger"
                    type="button"
                    onClick={() => handleBulkUpdate('delete')}
                    disabled={saving || selectedIds.length === 0}
                  >
                    Remove
                  </button>
                </div>
              </div>

              {selectedVisibleCount > 0 && (
                <p className="notifications-selection-count">
                  {selectedVisibleCount} notification{selectedVisibleCount === 1 ? '' : 's'} selected
                </p>
              )}

              {loading ? (
                <div className="notifications-empty-state">Loading notifications...</div>
              ) : filteredNotifications.length === 0 ? (
                <div className="notifications-empty-state">No notifications match your current search.</div>
              ) : (
                <>
                  <div className="notifications-list">
                    {paginatedNotifications.map((item) => (
                      <div
                        key={item.id}
                        className={`notification-card ${item.is_read ? 'notification-card-read' : 'notification-card-unread'}`}
                      >
                        <div className="notification-card-header">
                          <label className="notification-select">
                            <input
                              type="checkbox"
                              checked={selectedIds.includes(item.id)}
                              onChange={() => toggleSelection(item.id)}
                            />
                          </label>

                          <div className="notification-header-copy">
                            <h3 className="notification-title">{item.title}</h3>
                            <p className="notification-agency">{item.contract_title}</p>
                          </div>

                          <span className={getSeverityClassName(item.severity)}>
                            {item.severity === 'INFO' ? 'Update' : item.severity}
                          </span>
                        </div>

                        <div className="notification-meta-row">
                          <span className="notification-meta-item">
                            <strong>Agency:</strong> {item.contract_agency || 'Not provided'}
                          </span>
                          <span className="notification-meta-item">
                            <strong>Deadline:</strong> {formatDate(item.due_at)}
                          </span>
                          <span className="notification-meta-item">
                            <strong>Type:</strong> {item.notification_type}
                          </span>
                        </div>

                        <div className="notification-message-box">
                          {item.message}
                        </div>

                        <div className="notification-card-actions">
                          <button
                            className="notifications-inline-action"
                            type="button"
                            onClick={() => handleBulkUpdate(item.is_read ? 'unread' : 'read', [item.id])}
                            disabled={saving}
                          >
                            Mark as {item.is_read ? 'unread' : 'read'}
                          </button>
                          <button
                            className="notifications-inline-action notifications-inline-action-danger"
                            type="button"
                            onClick={() => handleBulkUpdate('delete', [item.id])}
                            disabled={saving}
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="notifications-pagination-row">
                    <p className="notifications-pagination-summary">
                      Showing {Math.min((currentPage - 1) * NOTIFICATIONS_PER_PAGE + 1, filteredNotifications.length)}-
                      {Math.min(currentPage * NOTIFICATIONS_PER_PAGE, filteredNotifications.length)} of {filteredNotifications.length}
                    </p>
                    <div className="notifications-pagination-controls">
                      <button
                        className="notifications-pagination-button"
                        type="button"
                        onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                        disabled={currentPage === 1}
                      >
                        Previous
                      </button>
                      <span className="notifications-pagination-indicator">
                        Page {currentPage} of {totalPages}
                      </span>
                      <button
                        className="notifications-pagination-button"
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
          </div>
        </main>
      </div>
    </div>
  );
}

export default NotificationsPage;
