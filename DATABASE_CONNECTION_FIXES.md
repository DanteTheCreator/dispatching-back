# Database Connection Leak Investigation and Fixes

## Investigation Summary

**Initial Problem**: Database connections were accumulating and not being properly released, leading to the database reaching its maximum connection limit (96/100 connections).

## Issues Identified

### 1. Multiple Route Builder Processes
- Found ~25 running instances of `route_builder_launcher.py`
- Each instance was creating and holding database connections
- Processes were being started repeatedly without killing old ones

### 2. Database Session Leaks in Multiple Files

#### `/route_building/driver.py`
- **Issue**: Created session with `next(get_db())` in constructor but never closed it
- **Fix**: Modified to create session in try/finally block and close it properly

#### `/route_building/route_builder_launcher.py` 
- **Issue**: Created session once outside the loop, never closed it
- **Fix**: Modified to create and close session for each iteration

#### `/zip_code_filler.py`
- **Issue**: Global session variable created but not properly managed
- **Fix**: Removed global session, create session locally with proper cleanup

#### `/selenium_agency/cleaner.py`
- **Issue**: Session created in constructor, not properly closed
- **Fix**: Modified to create session per operation with proper cleanup

#### `/selenium_agency/super_agency/super_agent.py`
- **Issue**: Session created in constructor and held indefinitely
- **Fix**: Modified to create sessions on-demand with proper cleanup methods

### 3. Database Connection Pool Configuration
- **Issue**: Pool size too large (5 + 10 overflow = 15 per process)
- **Fix**: Reduced to 3 + 5 overflow = 8 max per process

### 4. Idle Transaction Timeout
- **Issue**: No timeout for idle transactions, allowing them to accumulate
- **Fix**: Added `idle_in_transaction_session_timeout=60000` (60 seconds)

## Fixes Applied

### 1. Session Management Improvements
```python
# OLD - Session leak pattern:
self.db = next(get_db())  # Never closed

# NEW - Proper session management:
db = next(get_db())
try:
    # Use db session
finally:
    db.close()
```

### 2. Database Engine Configuration
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=3,  # Reduced from 5
    max_overflow=5,  # Reduced from 10
    pool_timeout=10,  # Reduced from 20
    pool_recycle=900,  # Reduced from 1800
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000",
        "application_name": "dispatching_api"
    }
)
```

### 3. Enhanced get_db() Function
- Added explicit rollback for uncommitted transactions
- Better error handling and cleanup

### 4. Process Management
- Killed all duplicate route_builder_launcher processes
- Created systemd service configuration for proper process management

## Results

**Before**: 96/100 database connections (critical)
**After**: 4/100 database connections (healthy)

## Monitoring

Created `monitor_db_connections.py` script to track:
- Total connections vs limit
- Connections by application and state
- Long-running idle transactions

## Recommendations

1. **Use the systemd service** for route_builder_launcher instead of manual execution
2. **Run the monitoring script periodically** to detect future connection leaks
3. **Always use dependency injection** (`Depends(get_db)`) for FastAPI endpoints
4. **For standalone scripts**, always use try/finally blocks for session management
5. **Avoid global database sessions** - create them when needed and close promptly

## Prevention Measures

1. All database sessions must be properly closed
2. Use context managers or try/finally blocks
3. Monitor connection counts regularly
4. Set appropriate timeout values
5. Use proper process management (systemd services)
