import sqlite3
import json
from datetime import datetime, timedelta
import uuid

class ContextManager:
    def __init__(self, db_path='context.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    ip_address TEXT
                )
            ''')
            
            # 创建对话历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    message TEXT,
                    role TEXT,  -- 'user' or 'assistant'
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            # 创建上下文实体表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS context_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    entity_type TEXT,  -- 'destination', 'days', 'budget', etc.
                    entity_value TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            # 创建生成的旅游规划表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS generated_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    plan_data TEXT,  -- JSON formatted plan data
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            conn.commit()
    
    def create_session(self, user_agent='', ip_address=''):
        """创建新会话"""
        session_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO sessions (session_id, user_agent, ip_address) VALUES (?, ?, ?)',
                (session_id, user_agent, ip_address)
            )
            conn.commit()
        return session_id
    
    def get_session(self, session_id):
        """获取会话信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM sessions WHERE session_id = ?',
                (session_id,)
            )
            return cursor.fetchone()
    
    def update_session_activity(self, session_id):
        """更新会话最后活动时间"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?',
                (session_id,)
            )
            conn.commit()
    
    def add_message(self, session_id, message, role):
        """添加对话消息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO conversation_history (session_id, message, role) VALUES (?, ?, ?)',
                (session_id, message, role)
            )
            conn.commit()
        self.update_session_activity(session_id)
    
    def get_conversation_history(self, session_id, limit=20):
        """获取对话历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT message, role, timestamp FROM conversation_history WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?',
                (session_id, limit)
            )
            results = cursor.fetchall()
        # 反转结果以按时间顺序返回
        return reversed(results)
    
    def add_context_entity(self, session_id, entity_type, entity_value):
        """添加上下文实体"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 先删除旧的相同类型的实体
            cursor.execute(
                'DELETE FROM context_entities WHERE session_id = ? AND entity_type = ?',
                (session_id, entity_type)
            )
            # 添加新实体
            cursor.execute(
                'INSERT INTO context_entities (session_id, entity_type, entity_value) VALUES (?, ?, ?)',
                (session_id, entity_type, entity_value)
            )
            conn.commit()
    
    def get_context_entities(self, session_id):
        """获取上下文实体"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT entity_type, entity_value FROM context_entities WHERE session_id = ?',
                (session_id,)
            )
            results = cursor.fetchall()
        return {entity_type: entity_value for entity_type, entity_value in results}
    
    def save_generated_plan(self, session_id, plan_data):
        """保存生成的旅游规划"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 先删除旧的规划
            cursor.execute(
                'DELETE FROM generated_plans WHERE session_id = ?',
                (session_id,)
            )
            # 添加新规划
            cursor.execute(
                'INSERT INTO generated_plans (session_id, plan_data) VALUES (?, ?)',
                (session_id, json.dumps(plan_data, ensure_ascii=False))
            )
            conn.commit()
    
    def get_generated_plan(self, session_id):
        """获取生成的旅游规划"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT plan_data FROM generated_plans WHERE session_id = ?',
                (session_id,)
            )
            result = cursor.fetchone()
        if result:
            return json.loads(result[0])
        return None
    
    def get_full_context(self, session_id):
        """获取完整上下文信息"""
        return {
            'conversation_history': list(self.get_conversation_history(session_id)),
            'context_entities': self.get_context_entities(session_id),
            'generated_plan': self.get_generated_plan(session_id)
        }
    
    def cleanup_expired_sessions(self, expiration_hours=24):
        """清理过期会话"""
        expiration_time = datetime.now() - timedelta(hours=expiration_hours)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 获取过期会话ID
            cursor.execute(
                'SELECT session_id FROM sessions WHERE last_activity < ?',
                (expiration_time.strftime('%Y-%m-%d %H:%M:%S'),)
            )
            expired_sessions = cursor.fetchall()
            
            for session_id, in expired_sessions:
                # 删除会话相关的所有数据
                cursor.execute('DELETE FROM conversation_history WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM context_entities WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM generated_plans WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            
            conn.commit()
        return len(expired_sessions)
