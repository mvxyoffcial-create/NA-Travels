"""
NA Travels - Admin Panel
HTML Admin Panel at /admin
API endpoints at /admin/api/*
"""
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template_string, session, redirect, url_for, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from app import mongo
from utils.helpers import (
    hash_password, check_password, save_image, delete_image,
    slugify, mongo_to_dict, now_utc, admin_required
)

admin_bp = Blueprint("admin", __name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  HTML ADMIN PANEL
# ═══════════════════════════════════════════════════════════════════════════════

ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NA Travels – Admin Panel</title>
<style>
  :root {
    --primary: #1a73e8; --primary-dark: #0d47a1; --danger: #e53935;
    --success: #2e7d32; --warning: #f57c00; --bg: #f0f2f5;
    --sidebar: #1e2a3a; --sidebar-text: #a0aec0; --card: #fff;
    --border: #e2e8f0; --text: #2d3748; --text-light: #718096;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); }
  
  /* Layout */
  #app { display: flex; min-height: 100vh; }
  .sidebar { width: 260px; background: var(--sidebar); color: var(--sidebar-text); flex-shrink: 0; display: flex; flex-direction: column; position: fixed; height: 100vh; overflow-y: auto; z-index: 100; }
  .main { margin-left: 260px; flex: 1; min-height: 100vh; }
  
  /* Sidebar */
  .sidebar-header { padding: 24px 20px; border-bottom: 1px solid #2d3748; }
  .sidebar-header h2 { color: #fff; font-size: 20px; }
  .sidebar-header p { font-size: 12px; color: #68d391; margin-top: 4px; }
  .sidebar nav { flex: 1; padding: 16px 0; }
  .nav-item { display: flex; align-items: center; gap: 12px; padding: 12px 20px; cursor: pointer; color: var(--sidebar-text); transition: all 0.2s; text-decoration: none; font-size: 14px; }
  .nav-item:hover, .nav-item.active { background: #2d3748; color: #fff; }
  .nav-item .icon { font-size: 18px; width: 22px; text-align: center; }
  .nav-label { font-weight: 500; }
  .sidebar-footer { padding: 16px 20px; border-top: 1px solid #2d3748; }
  .nav-section { padding: 8px 20px 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #4a5568; }
  
  /* Topbar */
  .topbar { background: var(--card); border-bottom: 1px solid var(--border); padding: 16px 28px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 50; }
  .topbar h1 { font-size: 20px; font-weight: 700; }
  .topbar-right { display: flex; align-items: center; gap: 16px; }
  .badge { background: var(--primary); color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
  
  /* Content */
  .content { padding: 28px; }
  
  /* Cards */
  .card { background: var(--card); border-radius: 12px; border: 1px solid var(--border); padding: 24px; margin-bottom: 24px; }
  .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
  .card-title { font-size: 16px; font-weight: 700; }
  
  /* Stats */
  .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 24px; }
  .stat-card { background: var(--card); border-radius: 12px; padding: 20px 24px; border: 1px solid var(--border); display: flex; align-items: center; gap: 16px; }
  .stat-icon { font-size: 32px; }
  .stat-value { font-size: 28px; font-weight: 800; line-height: 1; }
  .stat-label { font-size: 13px; color: var(--text-light); margin-top: 4px; }
  
  /* Table */
  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { background: #f7fafc; padding: 10px 16px; text-align: left; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-light); border-bottom: 2px solid var(--border); }
  td { padding: 12px 16px; border-bottom: 1px solid var(--border); }
  tr:hover td { background: #f7fafc; }
  
  /* Buttons */
  .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; text-decoration: none; }
  .btn-primary { background: var(--primary); color: #fff; }
  .btn-primary:hover { background: var(--primary-dark); }
  .btn-success { background: var(--success); color: #fff; }
  .btn-danger { background: var(--danger); color: #fff; }
  .btn-warning { background: var(--warning); color: #fff; }
  .btn-outline { background: transparent; color: var(--primary); border: 1.5px solid var(--primary); }
  .btn-sm { padding: 5px 10px; font-size: 12px; }
  
  /* Forms */
  .form-group { margin-bottom: 16px; }
  .form-label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--text); }
  .form-control { width: 100%; padding: 10px 14px; border: 1.5px solid var(--border); border-radius: 8px; font-size: 14px; transition: border-color 0.2s; background: #fff; }
  .form-control:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(26,115,232,0.1); }
  select.form-control { cursor: pointer; }
  textarea.form-control { resize: vertical; min-height: 100px; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  
  /* Modal */
  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; }
  .modal-overlay.open { display: flex; }
  .modal { background: #fff; border-radius: 16px; padding: 28px; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto; box-shadow: 0 25px 50px rgba(0,0,0,0.2); }
  .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
  .modal-title { font-size: 18px; font-weight: 700; }
  .modal-close { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-light); line-height: 1; }
  
  /* Login */
  .login-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: linear-gradient(135deg, #1e2a3a, #1a73e8); }
  .login-card { background: #fff; border-radius: 16px; padding: 40px; width: 380px; box-shadow: 0 25px 50px rgba(0,0,0,0.3); }
  .login-logo { text-align: center; margin-bottom: 32px; }
  .login-logo h1 { font-size: 28px; color: var(--primary); }
  .login-logo p { color: var(--text-light); font-size: 14px; margin-top: 4px; }
  
  /* Tags */
  .tag { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
  .tag-success { background: #c6f6d5; color: #22543d; }
  .tag-danger { background: #fed7d7; color: #742a2a; }
  .tag-warning { background: #fefcbf; color: #744210; }
  .tag-info { background: #bee3f8; color: #2a4365; }
  
  /* Alert */
  .alert { padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
  .alert-success { background: #c6f6d5; color: #22543d; border: 1px solid #9ae6b4; }
  .alert-danger { background: #fed7d7; color: #742a2a; border: 1px solid #fc8181; }
  
  /* Tabs */
  .tabs { display: flex; border-bottom: 2px solid var(--border); margin-bottom: 24px; }
  .tab { padding: 10px 20px; cursor: pointer; font-weight: 600; font-size: 14px; color: var(--text-light); border-bottom: 3px solid transparent; margin-bottom: -2px; }
  .tab.active { color: var(--primary); border-bottom-color: var(--primary); }
  
  /* Image preview */
  .img-preview { width: 60px; height: 60px; object-fit: cover; border-radius: 8px; border: 1px solid var(--border); }
  .img-preview-lg { width: 120px; height: 80px; object-fit: cover; border-radius: 8px; }
  
  /* Page sections */
  .page { display: none; }
  .page.active { display: block; }
  
  /* Responsive */
  @media (max-width: 768px) {
    .sidebar { transform: translateX(-100%); }
    .main { margin-left: 0; }
    .form-row { grid-template-columns: 1fr; }
    .stats-grid { grid-template-columns: 1fr 1fr; }
  }
  
  .loading { text-align: center; padding: 40px; color: var(--text-light); }
  .empty-state { text-align: center; padding: 60px 20px; color: var(--text-light); }
  .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
  
  /* Quill-like textarea for rich descriptions */
  .rich-textarea { min-height: 150px; }
  
  /* Photo grid */
  .photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
  .photo-item { position: relative; border-radius: 8px; overflow: hidden; aspect-ratio: 4/3; }
  .photo-item img { width: 100%; height: 100%; object-fit: cover; }
  .photo-item .photo-actions { position: absolute; top: 6px; right: 6px; display: flex; gap: 4px; opacity: 0; transition: opacity 0.2s; }
  .photo-item:hover .photo-actions { opacity: 1; }
  
  .pagination { display: flex; gap: 8px; margin-top: 16px; justify-content: center; }
  .page-btn { padding: 6px 12px; border: 1.5px solid var(--border); border-radius: 6px; cursor: pointer; font-size: 13px; background: #fff; }
  .page-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }
  .page-btn:hover:not(.active) { background: #f7fafc; }
</style>
</head>
<body>

<!-- LOGIN PAGE -->
<div id="loginPage" class="login-page">
  <div class="login-card">
    <div class="login-logo">
      <h1>✈️ NA Travels</h1>
      <p>Admin Panel</p>
    </div>
    <div id="loginAlert"></div>
    <div class="form-group">
      <label class="form-label">Email</label>
      <input type="email" id="loginEmail" class="form-control" placeholder="admin@natravels.com">
    </div>
    <div class="form-group">
      <label class="form-label">Password</label>
      <input type="password" id="loginPassword" class="form-control" placeholder="••••••••">
    </div>
    <button class="btn btn-primary" style="width:100%;justify-content:center;padding:12px" onclick="adminLogin()">
      Sign In →
    </button>
  </div>
</div>

<!-- ADMIN APP -->
<div id="adminApp" style="display:none">
<div id="app">
  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-header">
      <h2>✈️ NA Travels</h2>
      <p>Admin Dashboard</p>
    </div>
    <nav>
      <div class="nav-section">Main</div>
      <a class="nav-item active" onclick="showPage('dashboard')">
        <span class="icon">📊</span><span class="nav-label">Dashboard</span>
      </a>
      <div class="nav-section">Content</div>
      <a class="nav-item" onclick="showPage('destinations')">
        <span class="icon">🗺️</span><span class="nav-label">Destinations</span>
      </a>
      <a class="nav-item" onclick="showPage('photos')">
        <span class="icon">📸</span><span class="nav-label">Photos</span>
      </a>
      <a class="nav-item" onclick="showPage('reviews')">
        <span class="icon">⭐</span><span class="nav-label">Reviews</span>
      </a>
      <div class="nav-section">Management</div>
      <a class="nav-item" onclick="showPage('users')">
        <span class="icon">👥</span><span class="nav-label">Users</span>
      </a>
      <div class="nav-section">Settings</div>
      <a class="nav-item" onclick="adminLogout()">
        <span class="icon">🚪</span><span class="nav-label">Logout</span>
      </a>
    </nav>
  </div>

  <!-- Main Content -->
  <div class="main">
    <div class="topbar">
      <h1 id="pageTitle">Dashboard</h1>
      <div class="topbar-right">
        <span id="adminName" class="badge"></span>
      </div>
    </div>
    <div class="content">

      <!-- DASHBOARD -->
      <div id="page-dashboard" class="page active">
        <div class="stats-grid" id="statsGrid">
          <div class="stat-card"><span class="stat-icon">🗺️</span><div><div class="stat-value" id="stat-dest">—</div><div class="stat-label">Destinations</div></div></div>
          <div class="stat-card"><span class="stat-icon">👥</span><div><div class="stat-value" id="stat-users">—</div><div class="stat-label">Users</div></div></div>
          <div class="stat-card"><span class="stat-icon">⭐</span><div><div class="stat-value" id="stat-reviews">—</div><div class="stat-label">Reviews</div></div></div>
          <div class="stat-card"><span class="stat-icon">📸</span><div><div class="stat-value" id="stat-photos">—</div><div class="stat-label">Photos</div></div></div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Recent Users</span></div>
          <div id="recentUsers" class="loading">Loading...</div>
        </div>
      </div>

      <!-- DESTINATIONS -->
      <div id="page-destinations" class="page">
        <div class="card">
          <div class="card-header">
            <span class="card-title">All Destinations</span>
            <button class="btn btn-primary" onclick="openDestModal()">+ Add Destination</button>
          </div>
          <div id="alertDest"></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Photo</th><th>Name</th><th>Country</th><th>Category</th><th>Rating</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody id="destTableBody"><tr><td colspan="7" class="loading">Loading...</td></tr></tbody>
            </table>
          </div>
          <div class="pagination" id="destPagination"></div>
        </div>
      </div>

      <!-- PHOTOS -->
      <div id="page-photos" class="page">
        <div class="card">
          <div class="card-header">
            <span class="card-title">User Photos</span>
            <button class="btn btn-primary" onclick="openPhotoModal()">+ Add Photo</button>
          </div>
          <div id="alertPhoto"></div>
          <div id="photoGrid" class="loading">Loading...</div>
          <div class="pagination" id="photoPagination"></div>
        </div>
      </div>

      <!-- REVIEWS -->
      <div id="page-reviews" class="page">
        <div class="card">
          <div class="card-header"><span class="card-title">All Reviews</span></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>User</th><th>Destination</th><th>Rating</th><th>Review</th><th>Date</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody id="reviewTableBody"><tr><td colspan="7" class="loading">Loading...</td></tr></tbody>
            </table>
          </div>
          <div class="pagination" id="reviewPagination"></div>
        </div>
      </div>

      <!-- USERS -->
      <div id="page-users" class="page">
        <div class="card">
          <div class="card-header"><span class="card-title">All Users</span></div>
          <input type="text" class="form-control" style="margin-bottom:16px;max-width:300px" placeholder="Search users..." oninput="searchUsers(this.value)" id="userSearch">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Avatar</th><th>Name</th><th>Email</th><th>Provider</th><th>Role</th><th>Verified</th><th>Joined</th><th>Actions</th></tr></thead>
              <tbody id="userTableBody"><tr><td colspan="8" class="loading">Loading...</td></tr></tbody>
            </table>
          </div>
          <div class="pagination" id="userPagination"></div>
        </div>
      </div>

    </div><!-- /content -->
  </div><!-- /main -->
</div><!-- /app -->
</div><!-- /adminApp -->

<!-- DESTINATION MODAL -->
<div class="modal-overlay" id="destModal">
<div class="modal">
  <div class="modal-header">
    <span class="modal-title" id="destModalTitle">Add Destination</span>
    <button class="modal-close" onclick="closeModal('destModal')">&times;</button>
  </div>
  <div id="destModalAlert"></div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">Name *</label>
      <input type="text" id="dest-name" class="form-control" placeholder="e.g. Eiffel Tower">
    </div>
    <div class="form-group">
      <label class="form-label">Country *</label>
      <input type="text" id="dest-country" class="form-control" placeholder="e.g. France">
    </div>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">City / Location</label>
      <input type="text" id="dest-location" class="form-control" placeholder="e.g. Paris">
    </div>
    <div class="form-group">
      <label class="form-label">Category *</label>
      <select id="dest-category" class="form-control">
        <option value="">Select category</option>
        <option>Beach</option><option>Mountain</option><option>City</option>
        <option>Historical</option><option>Adventure</option><option>Cultural</option>
        <option>Wildlife</option><option>Island</option><option>Desert</option>
        <option>Winter</option><option>Cruise</option><option>Religious</option>
      </select>
    </div>
  </div>
  <div class="form-group">
    <label class="form-label">Short Description *</label>
    <input type="text" id="dest-short-desc" class="form-control" placeholder="One-line description">
  </div>
  <div class="form-group">
    <label class="form-label">Full Description</label>
    <textarea id="dest-description" class="form-control rich-textarea" placeholder="Detailed description..."></textarea>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">Best Time to Visit</label>
      <input type="text" id="dest-best-time" class="form-control" placeholder="e.g. April–October">
    </div>
    <div class="form-group">
      <label class="form-label">Budget Range</label>
      <select id="dest-budget" class="form-control">
        <option value="">Any</option>
        <option>Budget</option><option>Moderate</option><option>Luxury</option>
      </select>
    </div>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">Latitude</label>
      <input type="number" step="any" id="dest-lat" class="form-control" placeholder="e.g. 48.8566">
    </div>
    <div class="form-group">
      <label class="form-label">Longitude</label>
      <input type="number" step="any" id="dest-lng" class="form-control" placeholder="e.g. 2.3522">
    </div>
  </div>
  <div class="form-group">
    <label class="form-label">Cover Photo</label>
    <input type="file" id="dest-cover" class="form-control" accept="image/*">
    <div id="dest-cover-preview" style="margin-top:8px"></div>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">Published</label>
      <select id="dest-published" class="form-control">
        <option value="true">Yes – Live</option>
        <option value="false">No – Draft</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">Featured</label>
      <select id="dest-featured" class="form-control">
        <option value="false">No</option>
        <option value="true">Yes</option>
      </select>
    </div>
  </div>
  <input type="hidden" id="dest-edit-id">
  <div style="display:flex;gap:12px;justify-content:flex-end;margin-top:8px">
    <button class="btn btn-outline" onclick="closeModal('destModal')">Cancel</button>
    <button class="btn btn-primary" onclick="saveDestination()">Save Destination</button>
  </div>
</div>
</div>

<!-- PHOTO UPLOAD MODAL -->
<div class="modal-overlay" id="photoModal">
<div class="modal">
  <div class="modal-header">
    <span class="modal-title">Upload Destination Photo</span>
    <button class="modal-close" onclick="closeModal('photoModal')">&times;</button>
  </div>
  <div id="photoModalAlert"></div>
  <div class="form-group">
    <label class="form-label">Destination</label>
    <select id="photo-destination" class="form-control"></select>
  </div>
  <div class="form-group">
    <label class="form-label">Photo *</label>
    <input type="file" id="photo-file" class="form-control" accept="image/*">
  </div>
  <div class="form-group">
    <label class="form-label">Caption</label>
    <input type="text" id="photo-caption" class="form-control" placeholder="Optional caption">
  </div>
  <div style="display:flex;gap:12px;justify-content:flex-end;margin-top:8px">
    <button class="btn btn-outline" onclick="closeModal('photoModal')">Cancel</button>
    <button class="btn btn-primary" onclick="savePhoto()">Upload Photo</button>
  </div>
</div>
</div>

<script>
const API = '/admin/api';
let token = localStorage.getItem('admin_token');
let currentPage = {dest: 1, users: 1, reviews: 1, photos: 1};
let destEditId = null;

// ── AUTH ──────────────────────────────────────────────────────────────────────
async function adminLogin() {
  const email = document.getElementById('loginEmail').value;
  const pass = document.getElementById('loginPassword').value;
  const alertEl = document.getElementById('loginAlert');

  try {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email, password: pass})
    });
    const d = await r.json();
    if (!d.success) { showAlert(alertEl, d.message, 'danger'); return; }
    if (d.user.role !== 'admin') { showAlert(alertEl, 'Admin access required', 'danger'); return; }
    
    token = d.access_token;
    localStorage.setItem('admin_token', token);
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('adminApp').style.display = 'block';
    document.getElementById('adminName').textContent = d.user.full_name;
    loadDashboard();
  } catch(e) {
    showAlert(alertEl, 'Connection error', 'danger');
  }
}

function adminLogout() {
  localStorage.removeItem('admin_token');
  token = null;
  document.getElementById('loginPage').style.display = 'flex';
  document.getElementById('adminApp').style.display = 'none';
}

// Check existing token
(async function init() {
  if (!token) return;
  try {
    const r = await fetch('/api/auth/me', {headers: {'Authorization': 'Bearer ' + token}});
    const d = await r.json();
    if (d.success && d.user.role === 'admin') {
      document.getElementById('loginPage').style.display = 'none';
      document.getElementById('adminApp').style.display = 'block';
      document.getElementById('adminName').textContent = d.user.full_name;
      loadDashboard();
    } else {
      localStorage.removeItem('admin_token');
    }
  } catch(e) { localStorage.removeItem('admin_token'); }
})();

// ── NAVIGATION ────────────────────────────────────────────────────────────────
function showPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  event.currentTarget.classList.add('active');
  const titles = {dashboard:'Dashboard',destinations:'Destinations',photos:'Photos',reviews:'Reviews',users:'Users'};
  document.getElementById('pageTitle').textContent = titles[page] || page;
  
  if (page === 'dashboard') loadDashboard();
  if (page === 'destinations') loadDestinations();
  if (page === 'photos') loadPhotos();
  if (page === 'reviews') loadReviews();
  if (page === 'users') loadUsers();
}

// ── API HELPER ────────────────────────────────────────────────────────────────
async function api(path, opts = {}) {
  opts.headers = opts.headers || {};
  opts.headers['Authorization'] = 'Bearer ' + token;
  const r = await fetch(API + path, opts);
  return r.json();
}

// ── DASHBOARD ─────────────────────────────────────────────────────────────────
async function loadDashboard() {
  const d = await api('/stats');
  if (d.success) {
    document.getElementById('stat-dest').textContent = d.stats.destinations;
    document.getElementById('stat-users').textContent = d.stats.users;
    document.getElementById('stat-reviews').textContent = d.stats.reviews;
    document.getElementById('stat-photos').textContent = d.stats.photos;
  }
  
  const u = await api('/users?per_page=5');
  const el = document.getElementById('recentUsers');
  if (u.success) {
    el.innerHTML = `<table><thead><tr><th>Name</th><th>Email</th><th>Provider</th><th>Verified</th><th>Joined</th></tr></thead><tbody>
      ${u.users.map(user => `<tr>
        <td>${user.full_name}</td>
        <td>${user.email}</td>
        <td><span class="tag tag-info">${user.auth_provider}</span></td>
        <td>${user.is_verified ? '<span class="tag tag-success">Yes</span>' : '<span class="tag tag-danger">No</span>'}</td>
        <td>${formatDate(user.created_at)}</td>
      </tr>`).join('')}
    </tbody></table>`;
  }
}

// ── DESTINATIONS ──────────────────────────────────────────────────────────────
let allDestinations = [];

async function loadDestinations(page = 1) {
  currentPage.dest = page;
  const d = await api(`/destinations?page=${page}&per_page=10`);
  const tbody = document.getElementById('destTableBody');
  if (!d.success) { tbody.innerHTML = '<tr><td colspan="7">Error loading</td></tr>'; return; }
  
  allDestinations = d.destinations;
  
  if (!d.destinations.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#718096">No destinations yet. Add one!</td></tr>';
  } else {
    tbody.innerHTML = d.destinations.map(dest => `
      <tr>
        <td>${dest.cover_photo ? `<img src="${dest.cover_photo}" class="img-preview">` : '—'}</td>
        <td><strong>${dest.name}</strong><br><small style="color:#718096">${dest.location || ''}</small></td>
        <td>${dest.country}</td>
        <td><span class="tag tag-info">${dest.category || '—'}</span></td>
        <td>⭐ ${dest.average_rating || 0} (${dest.review_count || 0})</td>
        <td>${dest.is_published ? '<span class="tag tag-success">Live</span>' : '<span class="tag tag-warning">Draft</span>'}</td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="editDestination('${dest._id}')">Edit</button>
          <button class="btn btn-danger btn-sm" onclick="deleteDestination('${dest._id}','${dest.name}')">Delete</button>
        </td>
      </tr>
    `).join('');
  }
  
  renderPagination('destPagination', d.total, d.per_page, page, loadDestinations);
}

function openDestModal(editId = null) {
  destEditId = editId;
  document.getElementById('destModalAlert').innerHTML = '';
  document.getElementById('destModalTitle').textContent = editId ? 'Edit Destination' : 'Add Destination';
  if (!editId) {
    ['dest-name','dest-country','dest-location','dest-short-desc','dest-description',
     'dest-best-time','dest-lat','dest-lng'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('dest-category').value = '';
    document.getElementById('dest-budget').value = '';
    document.getElementById('dest-published').value = 'true';
    document.getElementById('dest-featured').value = 'false';
    document.getElementById('dest-edit-id').value = '';
    document.getElementById('dest-cover-preview').innerHTML = '';
  }
  document.getElementById('destModal').classList.add('open');
}

function editDestination(id) {
  const dest = allDestinations.find(d => d._id === id);
  if (!dest) return;
  document.getElementById('dest-name').value = dest.name || '';
  document.getElementById('dest-country').value = dest.country || '';
  document.getElementById('dest-location').value = dest.location || '';
  document.getElementById('dest-short-desc').value = dest.short_description || '';
  document.getElementById('dest-description').value = dest.description || '';
  document.getElementById('dest-best-time').value = dest.best_time || '';
  document.getElementById('dest-lat').value = dest.lat || '';
  document.getElementById('dest-lng').value = dest.lng || '';
  document.getElementById('dest-category').value = dest.category || '';
  document.getElementById('dest-budget').value = dest.budget_range || '';
  document.getElementById('dest-published').value = dest.is_published ? 'true' : 'false';
  document.getElementById('dest-featured').value = dest.is_featured ? 'true' : 'false';
  document.getElementById('dest-edit-id').value = id;
  if (dest.cover_photo) {
    document.getElementById('dest-cover-preview').innerHTML = `<img src="${dest.cover_photo}" style="height:80px;border-radius:6px;margin-top:8px">`;
  }
  openDestModal(id);
}

async function saveDestination() {
  const alertEl = document.getElementById('destModalAlert');
  const editId = document.getElementById('dest-edit-id').value;
  
  const fd = new FormData();
  fd.append('name', document.getElementById('dest-name').value.trim());
  fd.append('country', document.getElementById('dest-country').value.trim());
  fd.append('location', document.getElementById('dest-location').value.trim());
  fd.append('category', document.getElementById('dest-category').value);
  fd.append('short_description', document.getElementById('dest-short-desc').value.trim());
  fd.append('description', document.getElementById('dest-description').value.trim());
  fd.append('best_time', document.getElementById('dest-best-time').value.trim());
  fd.append('budget_range', document.getElementById('dest-budget').value);
  fd.append('lat', document.getElementById('dest-lat').value);
  fd.append('lng', document.getElementById('dest-lng').value);
  fd.append('is_published', document.getElementById('dest-published').value);
  fd.append('is_featured', document.getElementById('dest-featured').value);
  
  const coverFile = document.getElementById('dest-cover').files[0];
  if (coverFile) fd.append('cover_photo', coverFile);
  
  try {
    const method = editId ? 'PUT' : 'POST';
    const path = editId ? `/destinations/${editId}` : '/destinations';
    const r = await fetch(API + path, {
      method, headers: {'Authorization': 'Bearer ' + token}, body: fd
    });
    const d = await r.json();
    if (d.success) {
      closeModal('destModal');
      loadDestinations(currentPage.dest);
      showAlert(document.getElementById('alertDest'), d.message, 'success');
    } else {
      showAlert(alertEl, d.message, 'danger');
    }
  } catch(e) {
    showAlert(alertEl, 'Error saving destination', 'danger');
  }
}

async function deleteDestination(id, name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  const d = await api(`/destinations/${id}`, {method: 'DELETE'});
  if (d.success) {
    loadDestinations(currentPage.dest);
    showAlert(document.getElementById('alertDest'), 'Destination deleted', 'success');
  }
}

// ── PHOTOS ────────────────────────────────────────────────────────────────────
async function loadPhotos(page = 1) {
  currentPage.photos = page;
  const d = await api(`/photos?page=${page}&per_page=12`);
  const el = document.getElementById('photoGrid');
  if (!d.success) { el.innerHTML = '<p>Error loading photos</p>'; return; }
  
  if (!d.photos.length) {
    el.innerHTML = '<div class="empty-state"><div class="icon">📸</div><p>No photos yet</p></div>';
  } else {
    el.innerHTML = `<div class="photo-grid">${d.photos.map(p => `
      <div class="photo-item">
        <img src="${p.url}" alt="${p.caption || ''}">
        <div class="photo-actions">
          <button class="btn btn-danger btn-sm" onclick="deletePhoto('${p._id}')">🗑️</button>
        </div>
      </div>
    `).join('')}</div>`;
  }
  renderPagination('photoPagination', d.total, d.per_page, page, loadPhotos);
}

function openPhotoModal() {
  // Populate destination select
  const sel = document.getElementById('photo-destination');
  sel.innerHTML = allDestinations.map(d => `<option value="${d._id}">${d.name}</option>`).join('');
  document.getElementById('photoModal').classList.add('open');
}

async function savePhoto() {
  const alertEl = document.getElementById('photoModalAlert');
  const destId = document.getElementById('photo-destination').value;
  const file = document.getElementById('photo-file').files[0];
  
  if (!file) { showAlert(alertEl, 'Please select a photo', 'danger'); return; }
  
  const fd = new FormData();
  fd.append('photo', file);
  fd.append('caption', document.getElementById('photo-caption').value);
  
  try {
    const r = await fetch(`/admin/api/destinations/${destId}/photos`, {
      method: 'POST',
      headers: {'Authorization': 'Bearer ' + token},
      body: fd
    });
    const d = await r.json();
    if (d.success) {
      closeModal('photoModal');
      loadPhotos();
      showAlert(document.getElementById('alertPhoto'), 'Photo uploaded!', 'success');
    } else {
      showAlert(alertEl, d.message, 'danger');
    }
  } catch(e) { showAlert(alertEl, 'Upload error', 'danger'); }
}

async function deletePhoto(id) {
  if (!confirm('Delete this photo?')) return;
  const d = await api(`/photos/${id}`, {method: 'DELETE'});
  if (d.success) loadPhotos(currentPage.photos);
}

// ── REVIEWS ───────────────────────────────────────────────────────────────────
async function loadReviews(page = 1) {
  currentPage.reviews = page;
  const d = await api(`/reviews?page=${page}&per_page=10`);
  const tbody = document.getElementById('reviewTableBody');
  if (!d.success) { tbody.innerHTML = '<tr><td colspan="7">Error</td></tr>'; return; }
  
  if (!d.reviews.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px">No reviews yet</td></tr>';
  } else {
    tbody.innerHTML = d.reviews.map(r => `
      <tr>
        <td>${r.user_name}</td>
        <td>${r.destination_name || '—'}</td>
        <td>${'⭐'.repeat(Math.round(r.rating))} ${r.rating}</td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.body}</td>
        <td>${formatDate(r.created_at)}</td>
        <td>${r.is_approved ? '<span class="tag tag-success">Approved</span>' : '<span class="tag tag-warning">Pending</span>'}</td>
        <td>
          ${!r.is_approved ? `<button class="btn btn-success btn-sm" onclick="approveReview('${r._id}')">Approve</button>` : ''}
          <button class="btn btn-danger btn-sm" onclick="deleteReview('${r._id}')">Delete</button>
        </td>
      </tr>
    `).join('');
  }
  renderPagination('reviewPagination', d.total, d.per_page, page, loadReviews);
}

async function approveReview(id) {
  const d = await api(`/reviews/${id}/approve`, {method: 'POST'});
  if (d.success) loadReviews(currentPage.reviews);
}

async function deleteReview(id) {
  if (!confirm('Delete this review?')) return;
  const d = await api(`/reviews/${id}`, {method: 'DELETE'});
  if (d.success) loadReviews(currentPage.reviews);
}

// ── USERS ─────────────────────────────────────────────────────────────────────
async function loadUsers(page = 1) {
  currentPage.users = page;
  const search = document.getElementById('userSearch')?.value || '';
  const d = await api(`/users?page=${page}&per_page=10&search=${search}`);
  const tbody = document.getElementById('userTableBody');
  if (!d.success) { tbody.innerHTML = '<tr><td colspan="8">Error</td></tr>'; return; }
  
  tbody.innerHTML = d.users.map(u => `
    <tr>
      <td>${u.avatar ? `<img src="${u.avatar}" class="img-preview" style="width:40px;height:40px;border-radius:50%">` : '👤'}</td>
      <td><strong>${u.full_name}</strong><br><small>@${u.username}</small></td>
      <td>${u.email}</td>
      <td><span class="tag tag-info">${u.auth_provider}</span></td>
      <td><span class="tag ${u.role === 'admin' ? 'tag-warning' : 'tag-info'}">${u.role}</span></td>
      <td>${u.is_verified ? '<span class="tag tag-success">Yes</span>' : '<span class="tag tag-danger">No</span>'}</td>
      <td>${formatDate(u.created_at)}</td>
      <td>
        ${u.role !== 'admin' ? `<button class="btn btn-warning btn-sm" onclick="makeAdmin('${u._id}','${u.full_name}')">Make Admin</button>` : ''}
        <button class="btn btn-danger btn-sm" onclick="deleteUser('${u._id}','${u.full_name}')">Delete</button>
      </td>
    </tr>
  `).join('');
  
  renderPagination('userPagination', d.total, d.per_page, page, loadUsers);
}

let userSearchTimeout;
function searchUsers(val) {
  clearTimeout(userSearchTimeout);
  userSearchTimeout = setTimeout(() => loadUsers(1), 400);
}

async function makeAdmin(id, name) {
  if (!confirm(`Make "${name}" an admin?`)) return;
  const d = await api(`/users/${id}/role`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({role: 'admin'})
  });
  if (d.success) loadUsers();
}

async function deleteUser(id, name) {
  if (!confirm(`Delete user "${name}"? This cannot be undone.`)) return;
  const d = await api(`/users/${id}`, {method: 'DELETE'});
  if (d.success) loadUsers();
}

// ── HELPERS ───────────────────────────────────────────────────────────────────
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

function showAlert(el, msg, type) {
  el.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
  setTimeout(() => { if (el) el.innerHTML = ''; }, 4000);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', {year:'numeric',month:'short',day:'numeric'});
}

function renderPagination(containerId, total, perPage, currentPg, loadFn) {
  const pages = Math.ceil(total / perPage);
  const el = document.getElementById(containerId);
  if (pages <= 1) { el.innerHTML = ''; return; }
  
  let html = '';
  for (let i = 1; i <= pages; i++) {
    html += `<button class="page-btn ${i === currentPg ? 'active' : ''}" onclick="${loadFn.name}(${i})">${i}</button>`;
  }
  el.innerHTML = html;
}

// Close modal on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('open');
  });
});

// Enter key on login
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && document.getElementById('loginPage').style.display !== 'none') {
    adminLogin();
  }
});
</script>
</body>
</html>"""


# ── Serve Admin HTML ──────────────────────────────────────────────────────────
@admin_bp.route("/")
@admin_bp.route("")
def admin_panel():
    return render_template_string(ADMIN_HTML)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stats ─────────────────────────────────────────────────────────────────────
@admin_bp.route("/api/stats")
@jwt_required()
@admin_required
def get_stats():
    stats = {
        "destinations": mongo.db.destinations.count_documents({}),
        "users": mongo.db.users.count_documents({}),
        "reviews": mongo.db.reviews.count_documents({}),
        "photos": mongo.db.photos.count_documents({}),
        "pending_reviews": mongo.db.reviews.count_documents({"is_approved": False}),
    }
    return jsonify({"success": True, "stats": stats})


# ── Destinations CRUD ─────────────────────────────────────────────────────────
@admin_bp.route("/api/destinations")
@jwt_required()
@admin_required
def admin_list_destinations():
    from utils.helpers import get_pagination_params, paginate_cursor
    page, per_page = get_pagination_params()
    total = mongo.db.destinations.count_documents({})
    cursor = mongo.db.destinations.find().sort("created_at", -1)
    from utils.helpers import paginate_cursor
    result = paginate_cursor(cursor, page, per_page, total)
    return jsonify({"success": True, "destinations": mongo_to_dict(result["items"]),
                    "total": total, "per_page": per_page, "page": page})


@admin_bp.route("/api/destinations", methods=["POST"])
@jwt_required()
@admin_required
def admin_create_destination():
    name = request.form.get("name", "").strip()
    country = request.form.get("country", "").strip()

    if not name or not country:
        return jsonify({"success": False, "message": "Name and country are required"}), 400

    slug_base = slugify(name)
    slug = slug_base
    counter = 1
    while mongo.db.destinations.find_one({"slug": slug}):
        slug = f"{slug_base}-{counter}"
        counter += 1

    cover_path = None
    if "cover_photo" in request.files:
        cover_path = save_image(request.files["cover_photo"], "destinations")
        if cover_path:
            cover_path = f"/{cover_path}"

    doc = {
        "name": name,
        "slug": slug,
        "country": country,
        "location": request.form.get("location", "").strip(),
        "category": request.form.get("category", ""),
        "short_description": request.form.get("short_description", "").strip(),
        "description": request.form.get("description", "").strip(),
        "best_time": request.form.get("best_time", "").strip(),
        "budget_range": request.form.get("budget_range", ""),
        "cover_photo": cover_path,
        "photos": [],
        "lat": float(request.form.get("lat") or 0),
        "lng": float(request.form.get("lng") or 0),
        "is_published": request.form.get("is_published", "true").lower() == "true",
        "is_featured": request.form.get("is_featured", "false").lower() == "true",
        "average_rating": 0,
        "review_count": 0,
        "views": 0,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }

    result = mongo.db.destinations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "message": "Destination created", "destination": mongo_to_dict(doc)}), 201


@admin_bp.route("/api/destinations/<dest_id>", methods=["PUT"])
@jwt_required()
@admin_required
def admin_update_destination(dest_id):
    if not ObjectId.is_valid(dest_id):
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    dest = mongo.db.destinations.find_one({"_id": ObjectId(dest_id)})
    if not dest:
        return jsonify({"success": False, "message": "Destination not found"}), 404

    updates = {}
    fields = ["name", "country", "location", "category", "short_description",
              "description", "best_time", "budget_range"]
    for f in fields:
        val = request.form.get(f)
        if val is not None:
            updates[f] = val.strip()

    if request.form.get("lat"):
        updates["lat"] = float(request.form.get("lat"))
    if request.form.get("lng"):
        updates["lng"] = float(request.form.get("lng"))
    if request.form.get("is_published") is not None:
        updates["is_published"] = request.form.get("is_published").lower() == "true"
    if request.form.get("is_featured") is not None:
        updates["is_featured"] = request.form.get("is_featured").lower() == "true"

    if "cover_photo" in request.files:
        cover_path = save_image(request.files["cover_photo"], "destinations")
        if cover_path:
            if dest.get("cover_photo"):
                delete_image(dest["cover_photo"].lstrip("/"))
            updates["cover_photo"] = f"/{cover_path}"

    if not updates:
        return jsonify({"success": False, "message": "No fields to update"}), 400

    updates["updated_at"] = now_utc()
    mongo.db.destinations.update_one({"_id": ObjectId(dest_id)}, {"$set": updates})

    updated = mongo.db.destinations.find_one({"_id": ObjectId(dest_id)})
    return jsonify({"success": True, "message": "Destination updated", "destination": mongo_to_dict(updated)})


@admin_bp.route("/api/destinations/<dest_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def admin_delete_destination(dest_id):
    if not ObjectId.is_valid(dest_id):
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    dest = mongo.db.destinations.find_one({"_id": ObjectId(dest_id)})
    if not dest:
        return jsonify({"success": False, "message": "Destination not found"}), 404

    if dest.get("cover_photo"):
        delete_image(dest["cover_photo"].lstrip("/"))

    mongo.db.destinations.delete_one({"_id": ObjectId(dest_id)})
    mongo.db.reviews.delete_many({"destination_id": dest_id})
    mongo.db.photos.delete_many({"destination_id": dest_id})

    return jsonify({"success": True, "message": "Destination and all related content deleted"})


# ── Admin Upload Photo to Destination ────────────────────────────────────────
@admin_bp.route("/api/destinations/<dest_id>/photos", methods=["POST"])
@jwt_required()
@admin_required
def admin_upload_photo(dest_id):
    if "photo" not in request.files:
        return jsonify({"success": False, "message": "No photo provided"}), 400

    path = save_image(request.files["photo"], "destinations")
    if not path:
        return jsonify({"success": False, "message": "Invalid image"}), 400

    caption = request.form.get("caption", "")
    user_id = get_jwt_identity()
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})

    photo_doc = {
        "destination_id": dest_id,
        "user_id": user_id,
        "user_name": user.get("full_name") if user else "Admin",
        "user_username": "admin",
        "url": f"/{path}",
        "caption": caption,
        "likes": [], "likes_count": 0,
        "is_approved": True,
        "created_at": now_utc(),
    }
    result = mongo.db.photos.insert_one(photo_doc)
    photo_doc["_id"] = result.inserted_id

    # Also push to destination photos array
    mongo.db.destinations.update_one(
        {"_id": ObjectId(dest_id)},
        {"$push": {"photos": f"/{path}"}}
    )

    return jsonify({"success": True, "photo": mongo_to_dict(photo_doc)}), 201


# ── Admin Photos List ─────────────────────────────────────────────────────────
@admin_bp.route("/api/photos")
@jwt_required()
@admin_required
def admin_list_photos():
    from utils.helpers import get_pagination_params, paginate_cursor
    page, per_page = get_pagination_params()
    total = mongo.db.photos.count_documents({})
    cursor = mongo.db.photos.find().sort("created_at", -1)
    result = paginate_cursor(cursor, page, per_page, total)
    return jsonify({"success": True, "photos": mongo_to_dict(result["items"]),
                    "total": total, "per_page": per_page, "page": page})


@admin_bp.route("/api/photos/<photo_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def admin_delete_photo(photo_id):
    if not ObjectId.is_valid(photo_id):
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    photo = mongo.db.photos.find_one({"_id": ObjectId(photo_id)})
    if not photo:
        return jsonify({"success": False, "message": "Photo not found"}), 404

    delete_image(photo["url"].lstrip("/"))
    mongo.db.photos.delete_one({"_id": ObjectId(photo_id)})
    return jsonify({"success": True, "message": "Photo deleted"})


# ── Admin Reviews ─────────────────────────────────────────────────────────────
@admin_bp.route("/api/reviews")
@jwt_required()
@admin_required
def admin_list_reviews():
    from utils.helpers import get_pagination_params, paginate_cursor
    page, per_page = get_pagination_params()
    query = {}
    total = mongo.db.reviews.count_documents(query)
    cursor = mongo.db.reviews.find(query).sort("created_at", -1)
    result = paginate_cursor(cursor, page, per_page, total)
    return jsonify({"success": True, "reviews": mongo_to_dict(result["items"]),
                    "total": total, "per_page": per_page, "page": page})


@admin_bp.route("/api/reviews/<review_id>/approve", methods=["POST"])
@jwt_required()
@admin_required
def admin_approve_review(review_id):
    if not ObjectId.is_valid(review_id):
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    review = mongo.db.reviews.find_one({"_id": ObjectId(review_id)})
    if not review:
        return jsonify({"success": False, "message": "Review not found"}), 404

    mongo.db.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": {"is_approved": True, "updated_at": now_utc()}}
    )

    # Update rating
    from routes.reviews import _update_destination_rating
    _update_destination_rating(review["destination_id"])

    return jsonify({"success": True, "message": "Review approved"})


@admin_bp.route("/api/reviews/<review_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def admin_delete_review(review_id):
    if not ObjectId.is_valid(review_id):
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    review = mongo.db.reviews.find_one({"_id": ObjectId(review_id)})
    if not review:
        return jsonify({"success": False, "message": "Review not found"}), 404

    destination_id = review["destination_id"]
    mongo.db.reviews.delete_one({"_id": ObjectId(review_id)})

    from routes.reviews import _update_destination_rating
    _update_destination_rating(destination_id)

    return jsonify({"success": True, "message": "Review deleted"})


# ── Admin Users ───────────────────────────────────────────────────────────────
@admin_bp.route("/api/users")
@jwt_required()
@admin_required
def admin_list_users():
    from utils.helpers import get_pagination_params, paginate_cursor
    page, per_page = get_pagination_params()
    search = request.args.get("search", "").strip()

    query = {}
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
            {"username": {"$regex": search, "$options": "i"}},
        ]

    total = mongo.db.users.count_documents(query)
    cursor = mongo.db.users.find(query, {"password": 0}).sort("created_at", -1)
    result = paginate_cursor(cursor, page, per_page, total)

    return jsonify({"success": True, "users": mongo_to_dict(result["items"]),
                    "total": total, "per_page": per_page, "page": page})


@admin_bp.route("/api/users/<user_id>/role", methods=["PUT"])
@jwt_required()
@admin_required
def admin_update_role(user_id):
    if not ObjectId.is_valid(user_id):
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    data = request.get_json(silent=True) or {}
    role = data.get("role")
    if role not in ["user", "admin"]:
        return jsonify({"success": False, "message": "Invalid role"}), 400

    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": role, "updated_at": now_utc()}}
    )
    return jsonify({"success": True, "message": f"User role updated to {role}"})


@admin_bp.route("/api/users/<user_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def admin_delete_user(user_id):
    if not ObjectId.is_valid(user_id):
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    # Don't delete yourself
    current_user_id = get_jwt_identity()
    if user_id == current_user_id:
        return jsonify({"success": False, "message": "You cannot delete your own account"}), 403

    mongo.db.users.delete_one({"_id": ObjectId(user_id)})
    mongo.db.reviews.delete_many({"user_id": user_id})
    mongo.db.photos.delete_many({"user_id": user_id})

    return jsonify({"success": True, "message": "User and all their content deleted"})
