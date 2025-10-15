# Database Setup for Railway Deployment

Your app is now configured to use **PostgreSQL** on Railway while still supporting local JSON storage for development. Here's how to complete the setup:

## ✅ What's Already Done

1. **Database Module Created** (`database.py`)
   - Automatic detection of database vs JSON mode
   - Connection pooling for PostgreSQL
   - Backward compatibility with existing JSON files

2. **App Integration Complete** (`app.py`)
   - Now imports and uses database functions
   - Initializes database on startup
   - No code changes needed

3. **Dependencies Updated** (`requirements.txt`)
   - Added `psycopg2-binary==2.9.9` for PostgreSQL support

## 🚀 Next Steps: Configure PostgreSQL on Railway

### Step 1: Add PostgreSQL Service

1. Go to your Railway dashboard: https://railway.app/dashboard
2. Open your Chat bot project
3. Click **"+ New"** button
4. Select **"Database"**
5. Choose **"Add PostgreSQL"**
6. Railway will provision a PostgreSQL database

### Step 2: Get Database URL

1. Click on the newly created **PostgreSQL** service
2. Go to the **"Variables"** tab
3. Find the variable called **`DATABASE_URL`**
4. Click the copy icon to copy the full URL
   - It should look like: `postgresql://postgres:password@host:5432/railway`

### Step 3: Add DATABASE_URL to Your App

1. Go back to your main app service (not the PostgreSQL service)
2. Click on the **"Variables"** tab
3. Click **"+ New Variable"**
4. Enter:
   - **Variable name:** `DATABASE_URL`
   - **Value:** Paste the PostgreSQL URL you copied in Step 2
5. Click **"Add"**

### Step 4: Redeploy

Railway will automatically redeploy your app with the new environment variable. You can watch the deployment in the **"Deployments"** tab.

## ✅ How It Works

### Production (Railway with DATABASE_URL)
- App detects `DATABASE_URL` environment variable
- Uses PostgreSQL for persistent storage
- Creates tables automatically on first run:
  - `conversations`: Stores chat messages
  - `detailed_memories`: Stores media analysis

### Local Development (No DATABASE_URL)
- App uses JSON files in `memory/` folder
- No database needed for testing
- Same functionality, just file-based

## 🧪 Testing Your Database

After deployment, you can verify it's working:

1. **Send a message** to your deployed app
2. **Check Railway logs**:
   - Go to your app service
   - Click **"Logs"** tab
   - Look for: `[SUCCESS] Conversation saved to database`
   - You should see: `Using PostgreSQL database`

3. **Verify persistence**:
   - Refresh your browser
   - Your conversation history should remain
   - Previously, it would have been lost on refresh

## 📊 Database Schema

### `conversations` table:
```
- id (auto-increment)
- session_id (text)
- username (text)
- mode (text) - sustainability, chef, teacher, etc.
- user_message (text)
- bot_response (text)
- has_media (boolean)
- media_type (text) - image, video, audio
- timestamp (timestamp)
```

### `detailed_memories` table:
```
- id (auto-increment)
- session_id (text)
- media_type (text)
- timestamp (timestamp)
- detailed_analysis (text)
- extracted_memory (jsonb) - structured data
```

## 🔧 Troubleshooting

### "psycopg2 import error" in Railway logs
- This is normal if you see it briefly during deployment
- Railway installs packages from `requirements.txt` automatically
- Should resolve after deployment completes

### Conversations not saving
1. Check Railway logs for error messages
2. Verify `DATABASE_URL` is set in your app's variables
3. Make sure PostgreSQL service is running (green status)

### Want to migrate old conversations?
Your old JSON files in `memory/` are still there. If you want to migrate them to PostgreSQL:
1. Let me know - I can create a migration script
2. Or just start fresh with the database

## 🎉 Benefits

- **Persistent Storage**: Conversations survive app restarts
- **Scalability**: PostgreSQL handles multiple concurrent users
- **Backups**: Railway automatically backs up your database
- **Query Performance**: Faster than file-based storage
- **Production Ready**: Industry-standard database solution

## 📝 Notes

- Your local development still uses JSON files (no database needed)
- Railway's PostgreSQL includes automatic backups
- You can view/query your data using Railway's built-in database tools
- The database is private to your Railway project

---

**Need help?** Let me know if you encounter any issues during setup!
