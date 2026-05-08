"""Database operations - SQLite"""

import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Optional


DB_PATH = Path(__file__).parent.parent / "data" / "screener.db"


def init_db():
    """Initialize database schema"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Price history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            smma_fast REAL,
            smma_slow REAL,
            rsi REAL,
            adx REAL,
            plus_di REAL,
            minus_di REAL,
            signal INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, date)
        )
    """)
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ticker_date 
        ON price_history(ticker, date DESC)
    """)
    
    # Favorites table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            ticker TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)
    
    # Signals history (for backtesting and tracking)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            signal_date TEXT NOT NULL,
            price REAL,
            smma_fast REAL,
            smma_slow REAL,
            rsi REAL,
            adx REAL,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def save_price_data(ticker: str, df: pd.DataFrame):
    """Save price data with indicators to database"""
    conn = sqlite3.connect(DB_PATH)
    
    # Prepare data
    df = df.copy()
    df['ticker'] = ticker
    df['date'] = df.index.strftime('%Y-%m-%d')
    
    columns = ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']
    if 'smma_fast' in df.columns:
        columns.extend(['smma_fast', 'smma_slow', 'signal'])
    if 'rsi' in df.columns:
        columns.append('rsi')
    if 'adx' in df.columns:
        columns.extend(['adx', 'plus_di', 'minus_di'])
    
    df_to_save = df[columns]
    
    # Insert or replace
    df_to_save.to_sql('price_history', conn, if_exists='append', index=False, 
                      method='multi', chunksize=1000)
    
    conn.commit()
    conn.close()


def get_latest_date(ticker: str) -> Optional[str]:
    """Get the most recent date we have data for a ticker"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date FROM price_history 
        WHERE ticker = ? 
        ORDER BY date DESC 
        LIMIT 1
    """, (ticker,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None


def log_signal(ticker: str, signal_type: str, signal_date: str, 
               price: float, smma_fast: float, smma_slow: float, rsi: float = None, adx: float = None):
    """Log a detected signal"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO signals (ticker, signal_type, signal_date, price, smma_fast, smma_slow, rsi, adx)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ticker, signal_type, signal_date, price, smma_fast, smma_slow, rsi, adx))
    
    conn.commit()
    conn.close()


def add_favorite(ticker: str, notes: str = ""):
    """Add ticker to favorites"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO favorites (ticker, notes)
            VALUES (?, ?)
        """, (ticker, notes))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False  # Already exists
    
    conn.close()
    return success


def get_favorites() -> List[str]:
    """Get list of favorite tickers"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT ticker FROM favorites ORDER BY ticker")
    favorites = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return favorites


def remove_favorite(ticker: str):
    """Remove ticker from favorites"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM favorites WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print(f"✅ Database created at {DB_PATH}")
