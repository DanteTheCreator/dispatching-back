#!/usr/bin/env python3
"""
Database Connection Monitor
Monitor and display database connection information
"""

import psycopg2
from datetime import datetime

def monitor_connections():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',
            user='postgres',
            password='dispatchingisprofitable',
            port='5432'
        )
        cur = conn.cursor()
        
        print(f"=== Database Connection Monitor - {datetime.now()} ===")
        
        # Check total connections
        cur.execute("""
            SELECT count(*) as total_connections 
            FROM pg_stat_activity 
            WHERE datname = 'postgres';
        """)
        total = cur.fetchone()[0]
        
        # Check max connections
        cur.execute('SHOW max_connections;')
        max_conn = cur.fetchone()[0]
        
        print(f"Total connections: {total}/{max_conn}")
        
        # Check connections by application and state
        cur.execute("""
            SELECT application_name, state, count(*)
            FROM pg_stat_activity 
            WHERE datname = 'postgres' 
            AND pid != pg_backend_pid()
            GROUP BY application_name, state
            ORDER BY count(*) DESC;
        """)
        
        connections = cur.fetchall()
        if connections:
            print("\nConnections by application and state:")
            for app_name, state, count in connections:
                print(f"  {app_name or 'Unknown'}: {state} ({count})")
        else:
            print("\nNo active connections (other than this monitor)")
            
        # Check for long-running idle transactions
        cur.execute("""
            SELECT application_name, state, 
                   extract(epoch from (now() - state_change))::int as idle_seconds,
                   left(query, 50) as query_preview
            FROM pg_stat_activity 
            WHERE datname = 'postgres' 
            AND pid != pg_backend_pid()
            AND state = 'idle in transaction'
            AND extract(epoch from (now() - state_change)) > 60
            ORDER BY idle_seconds DESC;
        """)
        
        long_idle = cur.fetchall()
        if long_idle:
            print("\nLong-running idle transactions (>60 seconds):")
            for app_name, state, idle_seconds, query in long_idle:
                print(f"  {app_name or 'Unknown'}: {idle_seconds}s idle - {query}...")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    monitor_connections()
