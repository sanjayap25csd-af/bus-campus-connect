"""
Notification Service for Bus Campus Connect.
Dispatches and manages in-app notifications stored in the SQLite database.
"""

from database.db import query_db, execute_db


class NotificationService:
    @staticmethod
    def notify(user_id, title, message, notification_type='info'):
        """
        Create a new persistent notification in the database.
        notification_type: 'info', 'success', 'warning', 'danger'
        """
        sql = """
            INSERT INTO notifications (user_id, title, message, notification_type, is_read)
            VALUES (?, ?, ?, ?, 0)
        """
        return execute_db(sql, (user_id, title.strip(), message.strip(), notification_type))

    @staticmethod
    def get_user_notifications(user_id, limit=30):
        """Fetch notifications for a user ordered by newest first."""
        sql = """
            SELECT * FROM notifications 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        return query_db(sql, (user_id, limit))

    @staticmethod
    def get_unread_count(user_id):
        """Count unread notifications for navbar bell icon."""
        sql = "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0"
        res = query_db(sql, (user_id,), one=True)
        return res['cnt'] if res else 0

    @staticmethod
    def mark_as_read(notification_id, user_id):
        """Mark a single notification as read."""
        sql = "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?"
        execute_db(sql, (notification_id, user_id))

    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications for a user as read."""
        sql = "UPDATE notifications SET is_read = 1 WHERE user_id = ?"
        execute_db(sql, (user_id,))

