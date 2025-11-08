"""
Data Ingestion Module

Fetches OHLCV data from Binance, stores in database, handles multiple timeframes
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sqlite3
import yaml
from pathlib import Path


class DataIngestion:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize data ingestion with config"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
        self.db_path = "ml_trading_data.db"
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # OHLCV table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ohlcv (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe, timestamp)
            )
        ''')
        
        # Index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_timeframe_timestamp 
            ON ohlcv(symbol, timeframe, timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized")
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', 
                    since: Optional[datetime] = None, limit: int = 1000) -> pd.DataFrame:
        """
        Fetch OHLCV data from Binance
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1m', '5m', '1h')
            since: Start date (default: 90 days ago)
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with OHLCV data
        """
        if since is None:
            since = datetime.now() - timedelta(days=self.config['data']['history_days'])
        
        since_ms = int(since.timestamp() * 1000)
        
        try:
            print(f"📥 Fetching {symbol} {timeframe} data since {since.strftime('%Y-%m-%d')}...")
            
            all_ohlcv = []
            while True:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
                
                if not ohlcv:
                    break
                
                all_ohlcv.extend(ohlcv)
                
                # Update since to last timestamp + 1ms
                since_ms = ohlcv[-1][0] + 1
                
                # Break if we've caught up
                if len(ohlcv) < limit:
                    break
                
                print(f"   Fetched {len(all_ohlcv)} candles...")
            
            # Convert to DataFrame
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            df['timeframe'] = timeframe
            
            print(f"✅ Fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            print(f"❌ Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def store_ohlcv(self, df: pd.DataFrame):
        """Store OHLCV data in database"""
        if df.empty:
            return
        
        conn = sqlite3.connect(self.db_path)
        
        # Prepare data for insertion
        df_insert = df[['symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
        df_insert['timestamp'] = df_insert['timestamp'].astype(np.int64) // 10**6  # Convert to milliseconds
        
        # Insert in batches to avoid "too many SQL variables" error
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(df_insert), batch_size):
            batch = df_insert.iloc[i:i+batch_size]
            try:
                batch.to_sql('ohlcv', conn, if_exists='append', index=False, method='multi')
                total_inserted += len(batch)
            except sqlite3.IntegrityError:
                # Handle duplicates by inserting one at a time
                for _, row in batch.iterrows():
                    try:
                        row.to_frame().T.to_sql('ohlcv', conn, if_exists='append', index=False)
                        total_inserted += 1
                    except sqlite3.IntegrityError:
                        pass  # Skip duplicates
        
        conn.commit()
        conn.close()
        
        print(f"💾 Stored {total_inserted} candles in database")
    
    def load_ohlcv(self, symbol: str, timeframe: str = '1m', 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Load OHLCV data from database
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            start_date: Start date filter
            end_date: End date filter
        
        Returns:
            DataFrame with OHLCV data
        """
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
            SELECT timestamp, open, high, low, close, volume, symbol, timeframe
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
        """
        
        params = [symbol, timeframe]
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(int(start_date.timestamp() * 1000))
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(int(end_date.timestamp() * 1000))
        
        query += " ORDER BY timestamp ASC"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
    
    def update_all_symbols(self):
        """Fetch and store data for all configured symbols"""
        symbols = self.config['data']['symbols']
        timeframe = self.config['data']['timeframe']
        
        print(f"\n{'='*80}")
        print(f"📊 UPDATING DATA FOR {len(symbols)} SYMBOLS")
        print(f"{'='*80}\n")
        
        for symbol in symbols:
            try:
                # Fetch data
                df = self.fetch_ohlcv(symbol, timeframe)
                
                if not df.empty:
                    # Store in database
                    self.store_ohlcv(df)
                    print(f"✅ {symbol} updated\n")
                else:
                    print(f"⚠️  No data for {symbol}\n")
                    
            except Exception as e:
                print(f"❌ Error updating {symbol}: {e}\n")
        
        print(f"{'='*80}")
        print(f"✅ DATA UPDATE COMPLETE")
        print(f"{'='*80}\n")
    
    def get_latest_timestamp(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """Get the most recent timestamp for a symbol"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT MAX(timestamp) FROM ohlcv 
            WHERE symbol = ? AND timeframe = ?
        """, (symbol, timeframe))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        if result:
            return datetime.fromtimestamp(result / 1000)
        return None
    
    def incremental_update(self, symbol: str, timeframe: str = '1m'):
        """Fetch only new data since last stored timestamp"""
        latest = self.get_latest_timestamp(symbol, timeframe)
        
        if latest:
            # Fetch from 1 minute after latest
            since = latest + timedelta(minutes=1)
            print(f"📥 Incremental update for {symbol} from {since.strftime('%Y-%m-%d %H:%M')}")
        else:
            # First time fetch
            since = datetime.now() - timedelta(days=self.config['data']['history_days'])
            print(f"📥 Initial fetch for {symbol}")
        
        df = self.fetch_ohlcv(symbol, timeframe, since=since)
        
        if not df.empty:
            self.store_ohlcv(df)
            return len(df)
        return 0


def main():
    """Test data ingestion"""
    ingestion = DataIngestion()
    
    # Update all symbols
    ingestion.update_all_symbols()
    
    # Load and display sample
    print("\n📊 Sample Data for BTC/USDT:")
    df = ingestion.load_ohlcv('BTC/USDT', '1m')
    if not df.empty:
        print(f"   Total candles: {len(df)}")
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"\n{df.tail(10)}")


if __name__ == '__main__':
    main()

