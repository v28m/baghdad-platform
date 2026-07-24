import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('baghdad_platform.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                is_verified INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                bio TEXT DEFAULT '',
                join_date TEXT DEFAULT (datetime('now','localtime'))
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                likes_count INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                like_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (post_id) REFERENCES posts(post_id),
                UNIQUE(user_id, post_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (post_id) REFERENCES posts(post_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS follows (
                follow_id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL,
                following_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (follower_id) REFERENCES users(user_id),
                FOREIGN KEY (following_id) REFERENCES users(user_id),
                UNIQUE(follower_id, following_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        self.conn.commit()
    
    def user_exists(self, user_id):
        self.cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone() is not None
    
    def username_taken(self, username):
        self.cursor.execute('SELECT 1 FROM users WHERE username = ?', (username.lower(),))
        return self.cursor.fetchone() is not None
    
    def register_user(self, user_id, full_name, username):
        self.cursor.execute(
            'INSERT INTO users (user_id, full_name, username) VALUES (?, ?, ?)',
            (user_id, full_name, username.lower())
        )
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def get_user_by_username(self, username):
        self.cursor.execute('SELECT * FROM users WHERE username = ?', (username.lower(),))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        self.cursor.execute('SELECT * FROM users WHERE is_banned = 0')
        return self.cursor.fetchall()
    
    def get_users_count(self):
        self.cursor.execute('SELECT COUNT(*) FROM users')
        return self.cursor.fetchone()[0]
    
    def ban_user(self, user_id):
        self.cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id):
        self.cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def create_post(self, user_id, content):
        self.cursor.execute(
            'INSERT INTO posts (user_id, content) VALUES (?, ?)',
            (user_id, content)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_post(self, post_id):
        self.cursor.execute('''
            SELECT p.*, u.full_name, u.username, u.is_verified
            FROM posts p JOIN users u ON p.user_id = u.user_id
            WHERE p.post_id = ? AND p.is_deleted = 0
        ''', (post_id,))
        return self.cursor.fetchone()
    
    def get_user_posts(self, user_id, limit=20):
        self.cursor.execute('''
            SELECT p.*, u.full_name, u.username, u.is_verified
            FROM posts p JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = ? AND p.is_deleted = 0
            ORDER BY p.created_at DESC LIMIT ?
        ''', (user_id, limit))
        return self.cursor.fetchall()
    
    def get_timeline(self, user_id, limit=20):
        self.cursor.execute('''
            SELECT DISTINCT p.*, u.full_name, u.username, u.is_verified
            FROM posts p JOIN users u ON p.user_id = u.user_id
            LEFT JOIN follows f ON p.user_id = f.following_id
            WHERE p.is_deleted = 0 AND (f.follower_id = ? OR p.user_id = ?)
            ORDER BY p.created_at DESC LIMIT ?
        ''', (user_id, user_id, limit))
        return self.cursor.fetchall()
    
    def delete_post(self, post_id):
        self.cursor.execute('UPDATE posts SET is_deleted = 1 WHERE post_id = ?', (post_id,))
        self.conn.commit()
    
    def get_posts_count(self):
        self.cursor.execute('SELECT COUNT(*) FROM posts WHERE is_deleted = 0')
        return self.cursor.fetchone()[0]
    
    def toggle_like(self, user_id, post_id):
        self.cursor.execute('SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?', (user_id, post_id))
        if self.cursor.fetchone():
            self.cursor.execute('DELETE FROM likes WHERE user_id = ? AND post_id = ?', (user_id, post_id))
            self.cursor.execute('UPDATE posts SET likes_count = likes_count - 1 WHERE post_id = ?', (post_id,))
            self.conn.commit()
            return False
        else:
            self.cursor.execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)', (user_id, post_id))
            self.cursor.execute('UPDATE posts SET likes_count = likes_count + 1 WHERE post_id = ?', (post_id,))
            self.conn.commit()
            return True
    
    def has_liked(self, user_id, post_id):
        self.cursor.execute('SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?', (user_id, post_id))
        return self.cursor.fetchone() is not None
    
    def add_comment(self, user_id, post_id, content):
        self.cursor.execute(
            'INSERT INTO comments (user_id, post_id, content) VALUES (?, ?, ?)',
            (user_id, post_id, content)
        )
        self.cursor.execute('UPDATE posts SET comments_count = comments_count + 1 WHERE post_id = ?', (post_id,))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_comments(self, post_id, limit=10):
        self.cursor.execute('''
            SELECT c.*, u.full_name, u.username, u.is_verified
            FROM comments c JOIN users u ON c.user_id = u.user_id
            WHERE c.post_id = ?
            ORDER BY c.created_at DESC LIMIT ?
        ''', (post_id, limit))
        return self.cursor.fetchall()
    
    def request_verification(self, user_id, reason):
        self.cursor.execute(
            'INSERT INTO verification_requests (user_id, reason) VALUES (?, ?)',
            (user_id, reason)
        )
        self.conn.commit()
    
    def get_pending_verifications(self):
        self.cursor.execute('''
            SELECT vr.*, u.full_name, u.username
            FROM verification_requests vr JOIN users u ON vr.user_id = u.user_id
            WHERE vr.status = 'pending'
            ORDER BY vr.created_at DESC
        ''')
        return self.cursor.fetchall()
    
    def approve_verification(self, request_id, user_id):
        self.cursor.execute('UPDATE verification_requests SET status = "approved" WHERE request_id = ?', (request_id,))
        self.cursor.execute('UPDATE users SET is_verified = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def reject_verification(self, request_id):
        self.cursor.execute('UPDATE verification_requests SET status = "rejected" WHERE request_id = ?', (request_id,))
        self.conn.commit()
    
    def has_pending_verification(self, user_id):
        self.cursor.execute(
            'SELECT 1 FROM verification_requests WHERE user_id = ? AND status = "pending"',
            (user_id,)
        )
        return self.cursor.fetchone() is not None
    
    def toggle_follow(self, follower_id, following_id):
        if follower_id == following_id:
            return None
        self.cursor.execute(
            'SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?',
            (follower_id, following_id)
        )
        if self.cursor.fetchone():
            self.cursor.execute(
                'DELETE FROM follows WHERE follower_id = ? AND following_id = ?',
                (follower_id, following_id)
            )
            self.conn.commit()
            return False
        else:
            self.cursor.execute(
                'INSERT INTO follows (follower_id, following_id) VALUES (?, ?)',
                (follower_id, following_id)
            )
            self.conn.commit()
            return True
    
    def get_followers_count(self, user_id):
        self.cursor.execute('SELECT COUNT(*) FROM follows WHERE following_id = ?', (user_id,))
        return self.cursor.fetchone()[0]
    
    def get_following_count(self, user_id):
        self.cursor.execute('SELECT COUNT(*) FROM follows WHERE follower_id = ?', (user_id,))
        return self.cursor.fetchone()[0]
    
    def add_notification(self, user_id, message):
        self.cursor.execute(
            'INSERT INTO notifications (user_id, message) VALUES (?, ?)',
            (user_id, message)
        )
        self.conn.commit()
    
    def get_unread_notifications(self, user_id):
        self.cursor.execute(
            'SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC LIMIT 10',
            (user_id,)
        )
        return self.cursor.fetchall()
    
    def mark_notifications_read(self, user_id):
        self.cursor.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
