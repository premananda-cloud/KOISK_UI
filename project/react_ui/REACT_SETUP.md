# KOISK React UI Setup Guide

Complete setup guide for the React frontend with OAuth 2.0 authentication.

## 📋 Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Authentication Flow](#authentication-flow)
- [API Integration](#api-integration)
- [Deployment](#deployment)

## 📁 Project Structure

```
koisk-ui/
├── src/
│   ├── pages/
│   │   ├── Login.jsx           # OAuth2 login page
│   │   ├── Register.jsx        # User registration
│   │   └── Dashboard.jsx       # Main dashboard
│   ├── services/
│   │   ├── authService.js      # Authentication logic
│   │   └── apiService.js       # API requests
│   ├── store/
│   │   └── authStore.js        # Zustand auth store
│   ├── App.jsx                 # Main app component
│   ├── main.jsx                # Entry point
│   └── index.css               # Global styles
├── index.html                  # HTML template
├── vite.config.js             # Vite configuration
├── tailwind.config.js         # Tailwind CSS config
├── postcss.config.js          # PostCSS config
├── package.json               # Dependencies
└── .env.local.example         # Environment template
```

## 📦 Prerequisites

- Node.js 16+ (https://nodejs.org/)
- npm or yarn
- KOISK FastAPI backend running on http://localhost:8000

## 🚀 Installation

### 1. Clone or Download the Project

```bash
cd koisk-ui
```

### 2. Install Dependencies

```bash
npm install
```

This will install:
- `react` - UI framework
- `react-dom` - React DOM rendering
- `react-router-dom` - Client-side routing
- `zustand` - State management
- `axios` - HTTP client
- `tailwindcss` - Utility-first CSS
- `lucide-react` - Beautiful icons
- `date-fns` - Date utilities

### 3. Set Up Environment

Copy the environment template:

```bash
cp .env.local.example .env.local
```

Edit `.env.local`:

```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Google OAuth (optional)
VITE_GOOGLE_CLIENT_ID=your_google_client_id

# Feature Flags
VITE_ENABLE_GOOGLE_AUTH=true
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth Client ID | (optional) |
| `VITE_ENABLE_GOOGLE_AUTH` | Enable Google login | `true` |

### API Base URL

The API URL is configured in:
- `src/services/authService.js`
- `src/services/apiService.js`

Both use `import.meta.env.VITE_API_URL` from the environment.

## 🏃 Running the Application

### Development Mode

```bash
npm run dev
```

This starts the Vite dev server on `http://localhost:5173`

Features:
- Hot module replacement (HMR)
- Fast refresh on file changes
- API proxy to backend

### Build for Production

```bash
npm run build
```

Outputs optimized build to `dist/` folder

### Preview Production Build

```bash
npm run preview
```

Serves the production build locally for testing

## 🔐 Authentication Flow

### OAuth 2.0 Password Flow

1. **User Registration** (`/register`)
   - User enters username, email, password
   - Sent to `/api/v1/auth/register`
   - User account created in database
   - User redirected to login

2. **User Login** (`/login`)
   - User enters username and password
   - Sent to `/api/v1/auth/token` (OAuth2 Password Flow)
   - Backend validates credentials
   - Returns `access_token` and `refresh_token`
   - Tokens stored in `localStorage`
   - User redirected to dashboard

3. **Authenticated Requests**
   - All API requests include `Authorization: Bearer {access_token}` header
   - See `apiService.getAuthHeader()`

4. **Token Refresh**
   - When access token expires (401 response)
   - `refresh_token` used to get new `access_token`
   - See `apiService.request()` for automatic refresh

5. **Logout**
   - Tokens removed from `localStorage`
   - User redirected to login page

### Token Storage

Tokens are stored in browser's `localStorage`:

```javascript
localStorage.getItem('access_token')   // JWT access token
localStorage.getItem('refresh_token')  // JWT refresh token
localStorage.getItem('user')           // User object (JSON)
```

### Protected Routes

Routes are protected using the `ProtectedRoute` component in `App.jsx`:

```jsx
<Route
  path="/dashboard"
  element={
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  }
/>
```

## 🔗 API Integration

### Authentication Service

Located in `src/services/authService.js`

```javascript
import authService from './services/authService';

// Register
await authService.register(username, email, password, full_name);

// Login
await authService.login(username, password);

// Get current user
const user = authService.getCurrentUser();

// Check if authenticated
const isAuth = authService.isAuthenticated();

// Logout
authService.logout();

// Refresh token
await authService.refreshAccessToken();

// Get auth header
const headers = authService.getAuthHeader();
```

### API Service

Located in `src/services/apiService.js`

```javascript
import apiService from './services/apiService';

// Make authenticated request
const response = await apiService.request('/api/v1/electricity/pay-bill', {
  method: 'POST',
  body: JSON.stringify(data)
});

// Service-specific methods
await apiService.payElectricityBill(billData);
await apiService.payWaterBill(billData);
await apiService.payGasBill(billData);
```

### Zustand Store

Located in `src/store/authStore.js`

```javascript
import { useAuthStore } from './store/authStore';

export function MyComponent() {
  const { user, token, login, logout, isLoading, error } = useAuthStore();

  return (
    <div>
      {user && <p>Hello, {user.full_name}</p>}
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

## 🎨 Styling

### Tailwind CSS

The project uses Tailwind CSS for styling. Key configuration in `tailwind.config.js`.

### Global Styles

Global styles in `src/index.css`:
- CSS reset
- Tailwind directives
- Custom animations
- Scrollbar styling

### Component Styling

Components use Tailwind utility classes:

```jsx
<div className="flex items-center gap-4 p-6 bg-slate-800 rounded-lg">
  <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition">
    Click me
  </button>
</div>
```

## 📱 Responsive Design

All components are responsive using Tailwind's breakpoints:
- `sm:` - 640px and up
- `md:` - 768px and up
- `lg:` - 1024px and up
- `xl:` - 1280px and up

Example:

```jsx
<div className="grid md:grid-cols-3 gap-6">
  {/* 1 column on mobile, 3 columns on medium+ */}
</div>
```

## 🚀 Deployment

### Vercel (Recommended)

1. Push code to GitHub
2. Connect repository to Vercel
3. Set environment variables in Vercel dashboard:
   - `VITE_API_URL` = `https://api.yourdomain.com`
4. Deploy

### Netlify

1. Build the project: `npm run build`
2. Connect `dist` folder to Netlify
3. Set build command: `npm run build`
4. Set output directory: `dist`

### Self-Hosted

1. Build: `npm run build`
2. Copy `dist` folder to your server
3. Serve with nginx/Apache:

```nginx
server {
  listen 80;
  server_name yourdomain.com;
  root /path/to/dist;
  
  location / {
    try_files $uri $uri/ /index.html;
  }
  
  location /api {
    proxy_pass http://localhost:8000;
  }
}
```

## 🐛 Troubleshooting

### CORS Errors

Ensure FastAPI backend has correct CORS configuration in `.env`:

```env
CORS_ORIGINS=["http://localhost:5173", "https://yourdomain.com"]
```

### API Connection Issues

Check:
1. Backend is running on correct port
2. `VITE_API_URL` matches backend URL
3. Check browser console for errors
4. Verify API endpoints in `apiService.js`

### Authentication Issues

1. Clear browser storage: `localStorage.clear()`
2. Check token expiration: `ACCESS_TOKEN_EXPIRE_MINUTES` in backend
3. Verify credentials in database
4. Check JWT_SECRET is same on backend and frontend

### Build Issues

1. Clear cache: `rm -rf node_modules dist` then `npm install`
2. Update dependencies: `npm update`
3. Check Node version: `node --version` (should be 16+)

## 📚 Additional Resources

- [React Documentation](https://react.dev)
- [React Router](https://reactrouter.com)
- [Tailwind CSS](https://tailwindcss.com)
- [Zustand](https://github.com/pmndrs/zustand)
- [OAuth 2.0](https://oauth.net/2/)
- [JWT](https://jwt.io)

## 🤝 Contributing

1. Create a feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## 📄 License

Part of SUVIDHA 2026 framework

---

**Happy coding!** 🚀
