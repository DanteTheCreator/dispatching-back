from sqlalchemy import text
from typing import List

def execute_sql_query(self, query: str, params: dict = None) -> List:
    try:
        sql = text(query)
        
        # Execute the query with or without parameters
        if params:
            result = self.db.execute(sql, params)
        else:
            result = self.db.execute(sql)
        
        # Fetch all results
        rows = result.fetchall()
        return rows
        
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        print(f"Query: {query}")
        if params:
            print(f"Parameters: {params}")
        return []
