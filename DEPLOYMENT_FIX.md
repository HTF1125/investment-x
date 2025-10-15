# Deployment Fix for Investment-X

## Issues Identified

### 1. Missing `dnspython` Dependency
**Error:**
```
ConfigurationError: The "dnspython" module must be installed to use mongodb+srv:// URIs
```

**Fix:** Added `dnspython==2.7.0` to `requirements.txt`

### 2. Wrong Gunicorn Entry Point
**Error:**
```
ModuleNotFoundError: No module named 'ix.dash'
```

**Fix:** The application entry point should be `ix.web.app:server`, not `ix.dash`

### 3. Outdated MongoDB Drivers
**Issue:** Using pymongo 3.12.3 from 2021

**Fix:** Updated to:
- `pymongo==4.10.1`
- `motor==3.6.0`

## Files Updated

### 1. `requirements.txt`
- ✅ Added `dnspython==2.7.0`
- ✅ Updated `pymongo` from `3.12.3` to `4.10.1`
- ✅ Updated `motor` from `2.5.1` to `3.6.0`

### 2. `Procfile` (NEW)
Created a Procfile with the correct entry point:
```
web: gunicorn ix.web.app:server --bind 0.0.0.0:$PORT --workers 4 --timeout 120
```

### 3. `gunicorn_config.py` (NEW)
Created a gunicorn configuration file with optimal settings for production.

## How to Deploy

### Option A: Update Your Container/Platform Configuration

If you're using a cloud platform (Render, Heroku, Railway, etc.), update your service configuration:

**Change the start command from:**
- ❌ `gunicorn ix.dash:app`
- ❌ Any variation with `ix.dash`

**To:**
- ✅ `gunicorn ix.web.app:server --bind 0.0.0.0:$PORT --workers 4 --timeout 120`

**Or use the config file:**
- ✅ `gunicorn ix.web.app:server -c gunicorn_config.py`

### Option B: Platform-Specific Instructions

#### Render.com
1. Go to your service settings
2. Update the "Start Command" field to:
   ```
   gunicorn ix.web.app:server --bind 0.0.0.0:$PORT --workers 4 --timeout 120
   ```
3. Redeploy

#### Heroku
1. The `Procfile` will be automatically detected
2. Just push your changes:
   ```bash
   git add .
   git commit -m "Fix deployment configuration"
   git push heroku main
   ```

#### Docker
Update your Dockerfile's CMD instruction:
```dockerfile
CMD ["gunicorn", "ix.web.app:server", "-c", "gunicorn_config.py"]
```

#### Railway
1. Go to your service settings
2. Under "Deploy", update the start command to:
   ```
   gunicorn ix.web.app:server --bind 0.0.0.0:$PORT --workers 4 --timeout 120
   ```

### Option C: Use Procfile (Automatic)
If your platform supports Procfile (Heroku, some others), it will automatically use the command specified in the `Procfile` we created.

## Verification Steps

After deploying, check the logs for:

1. ✅ Successful MongoDB connection:
   ```
   Successfully connected to MongoDB: [database_name]
   ```

2. ✅ Gunicorn starting correctly:
   ```
   [INFO] Starting gunicorn
   [INFO] Listening at: http://0.0.0.0:8080
   [INFO] Booting worker with pid: X
   ```

3. ✅ No import errors for `ix.dash`

## Environment Variables Required

Make sure these environment variables are set in your deployment platform:

- `MONGODB_URL` or `DB_URL` - Your MongoDB connection string (mongodb+srv://...)
- `DB_NAME` - Your database name
- `PORT` - Port to bind to (usually set automatically by the platform)
- Any other app-specific environment variables

## Troubleshooting

### If you still see "No module named 'ix.dash'":
1. Clear your build cache on the platform
2. Ensure the start command is correctly set
3. Verify that `ix/web/app.py` exists in your repository

### If MongoDB connection still fails:
1. Verify your MongoDB connection string is correct
2. Check that your MongoDB Atlas IP whitelist includes your deployment platform's IPs (or use 0.0.0.0/0 for testing)
3. Verify your MongoDB user has the correct permissions

### If dependencies fail to install:
1. Ensure Python 3.11 is being used (as specified in `runtime.txt`)
2. Try clearing the build cache
3. Check platform-specific Python version compatibility

## Next Steps

1. Commit the changes:
   ```bash
   git add requirements.txt Procfile gunicorn_config.py
   git commit -m "Fix deployment: add dnspython, update pymongo, fix gunicorn entry point"
   ```

2. Push to your deployment platform:
   ```bash
   git push origin main
   ```

3. Update the start command in your platform's settings (if needed)

4. Monitor the deployment logs for successful startup

## Additional Notes

- The application will now properly expose the Flask server from the Dash app
- Gunicorn is configured with 4 workers and a 120-second timeout
- The configuration supports both `PORT` environment variable and defaults to 8080
- All MongoDB connection parameters have been optimized for production use
