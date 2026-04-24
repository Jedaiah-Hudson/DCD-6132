import { useEffect, useState } from 'react';

const NOTIFICATIONS_SUMMARY_API_URL = 'http://127.0.0.1:8000/api/notifications/summary/';

function useNotificationSummary() {
  const [unreadCount, setUnreadCount] = useState(0);
  const token = localStorage.getItem('token');

  useEffect(() => {
    if (!token) {
      setUnreadCount(0);
      return;
    }

    const controller = new AbortController();

    const loadNotificationSummary = async () => {
      try {
        const response = await fetch(NOTIFICATIONS_SUMMARY_API_URL, {
          signal: controller.signal,
          headers: {
            Authorization: `Token ${token}`,
          },
        });

        const data = await response.json();

        if (!response.ok) {
          return;
        }

        setUnreadCount(data.unread_count || 0);
      } catch (error) {
        if (error.name !== 'AbortError') {
          setUnreadCount(0);
        }
      }
    };

    loadNotificationSummary();

    return () => controller.abort();
  }, [token]);

  return unreadCount;
}

export default useNotificationSummary;
