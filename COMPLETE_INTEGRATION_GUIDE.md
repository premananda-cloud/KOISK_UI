# KOISK Complete Integration Guide
## React UI + OAuth 2.0 + PostgreSQL

This guide covers the complete setup and integration of the React frontend, OAuth 2.0 authentication, and PostgreSQL database.

## 📋 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        KOISK Application                         │
└─────────────────────────────────────────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ↓               ↓               ↓
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │   React UI   │  │   FastAPI    │  │  PostgreSQL  │
        │ (Port 5173)  │  │  (Port 8000) │  │  (Port 5432) │
        └──────────────┘  └──────────────┘  └──────────────┘
                │                │                │
                │ OAuth2         │ Database      │
                │ Password Flow  │ Queries       │
                │ JWT Tokens     │               │
                └────────────────┴───────────────┘
```

## 🚀 Complete Setup (Step by Step)

### Phase 1: Database Setup (PostgreSQL)

#### Step 1.1: Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Download from https://www.postgresql.org/download/windows/

#### Step 1.2: Create Database and User

```bash
sudo -u postgres psql

-- Inside PostgreSQL shell
CREATE USER koisk_user WITH PASSWORD 'koisk_password';
CREATE DATABASE koisk_db OWNER koisk_user;
GRANT ALL PRIVILEGES ON DATABASE koisk_db TO koisk_user;
\q
```

#### Step 1.3: Initialize Database Schema

```bash
cd /path/to/koisk-backend
psql -U koisk_user -h localhost -d koisk_db -f database/init.sql
```

Verify initialization:
```bash
psql -U koisk_user -d koisk_db -c "\dt"
```

Should show tables:
- users
- service_requests
- electricity_meters
- water_consumers
- gas_consumers
- payment_history

---

### Phase 2: Backend Setup (FastAPI + OAuth2)

#### Step 2.1: Create Virtual Environment

```bash
cd /path/to/koisk-backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 2.2: Install Dependencies

```bash
pip install -r requirements.txt
```

Update `requirements.txt` to include:
```txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-jose==3.3.0
passlib==1.7.4
python-dotenv==1.0.0
```

#### Step 2.3: Configure Environment

Create `.env`:

```env
# Database
DATABASE_URL=postgresql://koisk_user:koisk_password@localhost:5432/koisk_db

# Security
SECRET_KEY=your-super-secret-key-minimum-32-characters-long-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000", "https://yourdomain.com"]

# Logging
LOG_LEVEL=INFO
```

⚠️ **IMPORTANT:** Change `SECRET_KEY` to a strong random string:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Step 2.4: Update FastAPI App

Update `koisk_api.py`:

```python
# Add imports
from src.database.database import get_db, init_db
from src.api.auth_routes import router as auth_router
from src.security.auth import get_current_user

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")

# Include auth routes
app.include_router(auth_router)

# Example protected route
@app.get("/api/v1/user/profile")
async def get_user_profile(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user_id).first()
    return UserResponse.from_orm(user)
```

#### Step 2.5: Test Backend

Start the server:
```bash
python koisk_api.py
```

Test OAuth2:
```bash
# Register
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass123"

# Returns: { "access_token": "...", "refresh_token": "...", ... }
```

---

### Phase 3: Frontend Setup (React)

#### Step 3.1: Install Node.js

Download from https://nodejs.org/ (version 16+)

Verify:
```bash
node --version
npm --version
```

#### Step 3.2: Create React Project

Option A: From scratch
```bash
npm create vite@latest koisk-ui -- --template react
cd koisk-ui
npm install
```

Option B: Use provided structure
```bash
cd /path/to/koisk-ui
npm install
```

#### Step 3.3: Install Dependencies

```bash
npm install react-router-dom zustand axios lucide-react clsx date-fns
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

#### Step 3.4: Configure Environment

Create `.env.local`:

```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Google OAuth (optional)
VITE_GOOGLE_CLIENT_ID=your-google-client-id

# Features
VITE_ENABLE_GOOGLE_AUTH=true
```

#### Step 3.5: Project Structure

Ensure your React project has:
```
src/
├── pages/
│   ├── Login.jsx
│   ├── Register.jsx
│   └── Dashboard.jsx
├── services/
│   ├── authService.js
│   └── apiService.js
├── store/
│   └── authStore.js
├── App.jsx
├── main.jsx
└── index.css
```

#### Step 3.6: Start Development Server

```bash
npm run dev
```

Frontend runs on `http://localhost:5173`

---

### Phase 4: Integration Testing

#### Test 1: User Registration

1. Navigate to `http://localhost:5173/register`
2. Fill in registration form
3. Click "Create Account"
4. Verify user created in database:
   ```bash
   psql -U koisk_user -d koisk_db -c "SELECT * FROM users;"
   ```

#### Test 2: User Login

1. Navigate to `http://localhost:5173/login`
2. Enter credentials
3. Click "Sign In"
4. Should redirect to dashboard
5. Verify token in localStorage:
   ```javascript
   // In browser console
   localStorage.getItem('access_token')
   localStorage.getItem('user')
   ```

#### Test 3: Protected Routes

1. Logged in, navigate to `/dashboard`
2. Should display dashboard
3. Logout and try to access `/dashboard` directly
4. Should redirect to login

#### Test 4: API Requests

1. On dashboard, make a service request (pay bill, etc.)
2. Check database for new service_request:
   ```bash
   psql -U koisk_user -d koisk_db \
     -c "SELECT * FROM service_requests ORDER BY created_at DESC LIMIT 5;"
   ```

#### Test 5: Token Refresh

1. Wait for access token to expire (30 minutes)
2. Or set `ACCESS_TOKEN_EXPIRE_MINUTES=1` for testing
3. Make API request after expiration
4. Should automatically refresh token
5. Request should succeed

---

## 🔄 Complete Workflow

### User Registration & Login Flow

```
1. User visits http://localhost:5173
   ↓
2. Frontend redirects to /login (not authenticated)
   ↓
3. User fills registration form
   ↓
4. POST /api/v1/auth/register
   ├─ Backend validates input
   ├─ Hash password with bcrypt
   ├─ Insert into users table
   └─ Return success
   ↓
5. User logs in with credentials
   ↓
6. POST /api/v1/auth/token (OAuth2 Password Flow)
   ├─ Backend verifies username/password
   ├─ Create JWT access_token (30 min expiry)
   ├─ Create refresh_token (7 day expiry)
   └─ Return both tokens + user info
   ↓
7. Frontend stores tokens in localStorage
   ↓
8. Redirect to /dashboard
   ↓
9. All API requests include Authorization header:
   Authorization: Bearer {access_token}
   ↓
10. Backend verifies token with each request
    ├─ Valid: Process request
    ├─ Expired: Return 401
    └─ Invalid: Return 403
```

### Token Refresh Flow

```
1. User makes API request
2. Token is expired (401 response)
   ↓
3. Frontend intercepts 401
   ↓
4. POST /api/v1/auth/refresh
   ├─ Send refresh_token
   ├─ Backend validates refresh_token
   ├─ Generate new access_token
   └─ Return new tokens
   ↓
5. Frontend updates localStorage
   ↓
6. Retry original request with new token
   ↓
7. Request succeeds
```

---

## 🔐 Security Checklist

### Before Production Deployment

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DATABASE_URL` to production database
- [ ] Enable HTTPS everywhere
- [ ] Set `CORS_ORIGINS` to specific domains only
- [ ] Implement rate limiting on login endpoint
- [ ] Set up HTTPS certificates (Let's Encrypt)
- [ ] Configure password requirements (min 12 chars, complexity)
- [ ] Implement email verification
- [ ] Set up logging and monitoring
- [ ] Enable database backups
- [ ] Test all authentication flows
- [ ] Implement CSRF protection
- [ ] Set secure cookies (httpOnly, secure, sameSite)
- [ ] Monitor for suspicious login attempts
- [ ] Keep dependencies updated
- [ ] Implement API rate limiting
- [ ] Add request logging and monitoring

---

## 📊 Database Monitoring

### Check Database Status

```bash
# Connect to database
psql -U koisk_user -d koisk_db

# Show tables
\dt

# Show table sizes
\d+ users

# Count users
SELECT COUNT(*) FROM users;

# Count service requests
SELECT COUNT(*) FROM service_requests;

# Recent service requests
SELECT * FROM service_requests ORDER BY created_at DESC LIMIT 10;

# Exit
\q
```

### Backup Database

```bash
# Backup
pg_dump -U koisk_user -d koisk_db > backup.sql

# Restore
psql -U koisk_user -d koisk_db < backup.sql
```

---

## 🐛 Troubleshooting

### React Frontend Issues

**CORS Error:**
- Check `CORS_ORIGINS` in backend `.env`
- Should include `http://localhost:5173` for development
- Restart backend after changing

**Authentication Loop:**
- Clear localStorage: `localStorage.clear()`
- Check token in browser console
- Verify `VITE_API_URL` matches backend

**API Requests Failing:**
- Verify backend is running on port 8000
- Check network tab in browser DevTools
- Verify access_token is sent in headers

### Backend Issues

**Database Connection Error:**
```bash
# Check PostgreSQL running
sudo systemctl status postgresql

# Check credentials
psql -U koisk_user -h localhost -d koisk_db

# Check DATABASE_URL in .env
```

**Port Already in Use:**
```bash
# Find process on port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### PostgreSQL Issues

**Can't Connect:**
```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Check logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

**Database Locked:**
```bash
# Connect and check
psql -U postgres

SELECT * FROM pg_stat_activity WHERE datname = 'koisk_db';

# Terminate blocking connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE datname = 'koisk_db' AND pid <> pg_backend_pid();
```

---

## 📚 Environment Variables Reference

| Variable | Backend | Frontend | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | ✅ | ❌ | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | ❌ | JWT signing key (min 32 chars) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ | ❌ | Access token lifetime |
| `CORS_ORIGINS` | ✅ | ❌ | Allowed frontend URLs |
| `VITE_API_URL` | ❌ | ✅ | Backend API URL |
| `VITE_GOOGLE_CLIENT_ID` | ❌ | ✅ | Google OAuth client ID |

---

## 🚀 Deployment

### Deploy Backend (Gunicorn + Nginx)

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn koisk_api:app -w 4 -b 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker

# Use systemd for auto-restart (see GETTING_STARTED.md)
```

### Deploy Frontend (Vercel/Netlify)

```bash
# Build
npm run build

# Deploy dist folder to Vercel/Netlify
```

### Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# Access
# Frontend: http://localhost
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## 📖 Documentation Files

- **REACT_SETUP.md** - React development guide
- **DATABASE_OAUTH2_GUIDE.md** - Database and security details
- **README.md** - Backend API documentation
- **GETTING_STARTED.md** - Quick start guide

---

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OAuth 2.0 Specification](https://oauth.net/2/)
- [JWT (JSON Web Tokens)](https://jwt.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)

---

## ✅ Checklist: Full Setup

- [ ] PostgreSQL installed and running
- [ ] Database created (koisk_db)
- [ ] Database schema initialized
- [ ] Backend environment configured (.env)
- [ ] Backend dependencies installed
- [ ] Backend running on :8000
- [ ] Frontend environment configured (.env.local)
- [ ] Frontend dependencies installed
- [ ] Frontend running on :5173
- [ ] Can register new user
- [ ] Can login with credentials
- [ ] Can access protected routes
- [ ] API requests working
- [ ] Service requests saving to database
- [ ] Token refresh working
- [ ] Logout working

---

**Congratulations!** 🎉 Your complete KOISK application is set up and running!

For support, refer to the individual documentation files or troubleshooting sections.
