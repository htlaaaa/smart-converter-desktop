"""
数据库管理
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger


class Database:
    """数据库管理"""

    def __init__(self, db_path: str = "data/converter.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT NOT NULL,
                platform TEXT,
                item_id TEXT,
                title TEXT,
                promote_url TEXT,
                tao_password TEXT,
                price REAL,
                commission_rate REAL,
                commission_amount REAL,
                ai_analysis TEXT,
                copywriting TEXT,
                status TEXT DEFAULT 'success',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS batch_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT UNIQUE NOT NULL,
                total_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'processing',
                progress REAL DEFAULT 0,
                result_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_conversions_created_at ON conversions(created_at);
            CREATE INDEX IF NOT EXISTS idx_conversions_platform ON conversions(platform);
        """)

        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")

    def save_conversion(self, data: Dict) -> int:
        """保存转链记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO conversions (
                original_url, platform, item_id, title,
                promote_url, tao_password, price,
                commission_rate, commission_amount,
                ai_analysis, copywriting
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('original_url'),
            data.get('platform'),
            data.get('item_id'),
            data.get('title'),
            data.get('promote_url'),
            data.get('tao_password'),
            data.get('price'),
            data.get('commission_rate'),
            data.get('commission_amount'),
            data.get('ai_analysis'),
            data.get('copywriting'),
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"保存转链记录: id={record_id}")
        return record_id

    def get_conversions(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取转链记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM conversions
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_conversion_by_id(self, record_id: int) -> Optional[Dict]:
        """根据 ID 获取记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM conversions WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def search_conversions(self, keyword: str) -> List[Dict]:
        """搜索转链记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM conversions
            WHERE title LIKE ? OR original_url LIKE ?
            ORDER BY created_at DESC
            LIMIT 100
        """, (f"%{keyword}%", f"%{keyword}%"))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def delete_conversion(self, record_id: int) -> bool:
        """删除转链记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM conversions WHERE id = ?", (record_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM conversions")
        total = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as today FROM conversions WHERE date(created_at) = date('now')")
        today = cursor.fetchone()['today']

        cursor.execute("SELECT SUM(commission_amount) as total_commission FROM conversions")
        total_commission = cursor.fetchone()['total_commission'] or 0

        cursor.execute("""
            SELECT platform, COUNT(*) as count
            FROM conversions
            GROUP BY platform
        """)
        platform_stats = {row['platform']: row['count'] for row in cursor.fetchall()}

        conn.close()

        return {
            "total_conversions": total,
            "today_conversions": today,
            "total_commission": total_commission,
            "platform_stats": platform_stats,
        }
