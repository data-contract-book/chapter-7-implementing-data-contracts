import pandas as pd
from psycopg_pool import ConnectionPool
import socket

class PostgresDB:
    def __init__(self):
        """Initialize database connection."""
        # Try to connect to postgres service first (works in Codespaces/devcontainer)
        # If that fails, fall back to localhost (works locally)
        try:
            # Test if we can reach the postgres service
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('postgres', 5432))
            sock.close()
            
            if result == 0:
                # postgres service is reachable (Codespaces/devcontainer)
                self.db_url = "postgresql://postgres:postgres@postgres:5432/postgres"
            else:
                # fall back to localhost (local development)
                self.db_url = "postgresql://postgres:postgres@localhost:5432/postgres"
        except:
            # If socket test fails, use localhost
            self.db_url = "postgresql://postgres:postgres@localhost:5432/postgres"
            
        self.pool = None
    
    def _get_pool(self):
        """Get or create a connection pool."""
        if self.pool is None or self.pool.closed:
            self.pool = ConnectionPool(self.db_url, min_size=1, max_size=5, open=True)
        return self.pool
    
    def query(self, sql_query: str) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame."""
        
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                results = cur.fetchall()
                
                # Get column names
                column_names = [desc[0] for desc in cur.description]
                
                # Create DataFrame manually
                df = pd.DataFrame(results, columns=column_names)
                return df
    
    def __del__(self):
        """Clean up the connection pool when the object is destroyed."""
        if self.pool and not self.pool.closed:
            self.pool.close()
