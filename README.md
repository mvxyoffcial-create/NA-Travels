# ✈️ NA Travels — Backend API

**Python/Flask REST API** for the NA Travels tourist website.  
Deployable on **Koyeb** | Database: **MongoDB Atlas**

---

## 🚀 Quick Deploy to Koyeb

1. Push this folder to GitHub
2. Create a new Koyeb service → connect your GitHub repo
3. Set **Build command**: `pip install -r requirements.txt`
4. Set **Run command**: `gunicorn app:create_app() --bind 0.0.0.0:$PORT --workers 2 --threads 4`
5. Add all environment variables from `.env.example` in Koyeb dashboard

---

## ⚙️ Environment Variables (set in Koyeb dashboard)

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask secret key (min 32 chars, random) |
| `MONGO_URI` | MongoDB Atlas connection string |
| `JWT_SECRET_KEY` | JWT signing key (min 32 chars, random) |
| `MAIL_USERNAME` | Gmail address |
| `MAIL_PASSWORD` | Gmail App Password (not your Gmail password) |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `FRONTEND_URL` | Your frontend domain e.g. `https://natravels.com` |
| `ADMIN_EMAIL` | Default admin email |
| `ADMIN_PASSWORD` | Default admin password |

---

## 📖 API Endpoints

Base URL: `https://your-koyeb-app.koyeb.app`

### 🔐 Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | ❌ | Register with email + password |
| POST | `/api/auth/login` | ❌ | Login with email + password |
| POST | `/api/auth/google` | ❌ | Login/signup with Google ID token |
| POST | `/api/auth/verify-email` | ❌ | Verify email with token |
| POST | `/api/auth/resend-verification` | ❌ | Resend verification email |
| POST | `/api/auth/forgot-password` | ❌ | Send password reset email |
| POST | `/api/auth/reset-password` | ❌ | Reset password with token |
| POST | `/api/auth/refresh` | 🔄 Refresh | Get new access token |
| POST | `/api/auth/logout` | ✅ JWT | Logout |
| GET | `/api/auth/me` | ✅ JWT | Get current user |

#### Register
```json
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "Password123",
  "full_name": "John Doe",
  "username": "johndoe"
}
```

#### Login
```json
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "Password123"
}
// Response:
{
  "success": true,
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": { "id": "...", "email": "...", "role": "user", ... }
}
```

#### Google Login
```json
POST /api/auth/google
{
  "id_token": "google-id-token-from-frontend"
}
```

#### Verify Email
```json
POST /api/auth/verify-email
{
  "token": "token-from-email-link"
}
```

#### Forgot Password
```json
POST /api/auth/forgot-password
{ "email": "user@example.com" }
```

#### Reset Password
```json
POST /api/auth/reset-password
{
  "token": "token-from-email",
  "password": "NewPassword123"
}
```

---

### 👤 User Profile

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/user/profile` | ✅ JWT | Get own profile |
| PUT | `/api/user/profile` | ✅ JWT | Update profile |
| POST | `/api/user/avatar` | ✅ JWT | Upload avatar (multipart) |
| DELETE | `/api/user/avatar` | ✅ JWT | Remove avatar |
| POST | `/api/user/change-password` | ✅ JWT | Change password |
| GET | `/api/user/favorites` | ✅ JWT | Get favorite destinations |
| POST | `/api/user/favorites/:id` | ✅ JWT | Add to favorites |
| DELETE | `/api/user/favorites/:id` | ✅ JWT | Remove from favorites |
| GET | `/api/user/reviews` | ✅ JWT | Get own reviews |
| GET | `/api/user/:username` | ❌ | Public user profile |

---

### 🗺️ Destinations

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/destinations/` | ❌ | List destinations (paginated) |
| GET | `/api/destinations/featured` | ❌ | Featured destinations |
| GET | `/api/destinations/categories` | ❌ | All categories + counts |
| GET | `/api/destinations/countries` | ❌ | All countries + counts |
| GET | `/api/destinations/:slug` | ❌ | Single destination by slug or ID |

**Query params for listing:**
- `q` — search text
- `category` — filter by category
- `country` — filter by country
- `sort` — `created_at` | `rating` | `popular` | `name`
- `page`, `per_page`

---

### ⭐ Reviews

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/reviews/destination/:id` | ❌ | Get reviews for destination |
| POST | `/api/reviews/destination/:id` | ✅ JWT | Create review |
| PUT | `/api/reviews/:id` | ✅ JWT | Update own review |
| DELETE | `/api/reviews/:id` | ✅ JWT | Delete own review |
| POST | `/api/reviews/:id/like` | ✅ JWT | Like/unlike review |
| GET | `/api/reviews/:id` | ❌ | Get single review |

#### Create Review
```json
POST /api/reviews/destination/:id
Headers: Authorization: Bearer <token>
{
  "rating": 4.5,
  "title": "Amazing place!",
  "body": "We had an incredible time visiting this destination...",
  "visit_date": "2024-03",
  "travel_type": "couple"
}
```

---

### 📸 Photos

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/photos/review/:id` | ✅ JWT | Add photos to review (multipart, field: `photos[]`) |
| POST | `/api/photos/destination/:id` | ✅ JWT | Upload destination photo (multipart, field: `photo`) |
| GET | `/api/photos/destination/:id` | ❌ | Get all photos for destination |
| DELETE | `/api/photos/:id` | ✅ JWT | Delete own photo |
| POST | `/api/photos/:id/like` | ✅ JWT | Like/unlike photo |

---

### 🔧 Admin Panel

| URL | Description |
|---|---|
| `/admin` | Admin HTML panel (login with admin email/password) |
| `/admin/api/stats` | Dashboard stats |
| `/admin/api/destinations` | CRUD destinations |
| `/admin/api/destinations/:id/photos` | Upload photos to destination |
| `/admin/api/photos` | List / delete all photos |
| `/admin/api/reviews` | List / approve / delete reviews |
| `/admin/api/users` | List / manage users |
| `/admin/api/users/:id/role` | Change user role |

All `/admin/api/*` endpoints require `Authorization: Bearer <token>` with admin role.

---

## 🔑 Using JWT

Include the token in every authenticated request:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
```

Access tokens expire in **1 hour**. Use the refresh token to get a new one:
```json
POST /api/auth/refresh
Headers: Authorization: Bearer <refresh_token>
```

---

## 🌐 CORS

CORS is configured to allow requests from `FRONTEND_URL`. Add additional origins in `app.py` if needed.

---

## 📁 Static Files

Uploaded images are served at:
- `/static/uploads/photos/<filename>` — review photos
- `/static/uploads/avatars/<filename>` — user avatars  
- `/static/uploads/destinations/<filename>` — destination photos

> **Note for production**: Use a CDN (Cloudflare, AWS S3) for file storage in production. The current implementation stores files on the server which resets on Koyeb deploys.

---

## 🗄️ MongoDB Collections

| Collection | Description |
|---|---|
| `users` | User accounts |
| `destinations` | Travel destinations |
| `reviews` | User reviews |
| `photos` | Gallery photos |

---

## 🔒 Security Features

- Passwords hashed with **bcrypt**
- **JWT** access + refresh tokens
- Email tokens signed with **itsdangerous** (time-limited)
- **Rate limiting** on auth endpoints
- Input validation throughout
- Admin role protection
- CORS restricted to allowed origins

---

## 📧 Gmail Setup

1. Enable 2FA on your Gmail account
2. Go to Google Account → Security → App Passwords
3. Create an App Password for "Mail"
4. Use this 16-char password as `MAIL_PASSWORD`

---

## 🌍 Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable Google+ API
3. Create OAuth 2.0 credentials
4. Add your frontend domain to authorized origins
5. Copy Client ID → `GOOGLE_CLIENT_ID`

---

## 📦 Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
