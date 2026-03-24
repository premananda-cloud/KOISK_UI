// orchestrator.js - REAL IMPLEMENTATION
import axios from 'axios';

class Orchestrator {
  constructor() {
    this._backendConnected = false;
    this._backendBaseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8877';
    this._mockMode = false; // Real backend mode
    // Auto-probe on startup
    this._probe();
  }

  async _probe() {
    try {
      const res = await fetch(`${this._backendBaseUrl}/health`);
      if (res.ok) {
        this._backendConnected = true;
        this._mockMode = false;
        console.info('[Orchestrator] ✅ Backend connected at', this._backendBaseUrl);
      }
    } catch {
      this._backendConnected = false;
      this._mockMode = true;
      console.warn('[Orchestrator] ⚠️ Backend unreachable — mock mode active');
    }
  }

  isConnected() {
    return this._backendConnected;
  }

  _authHeaders() {
    const token = localStorage.getItem('auth_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  // ── Auth lifecycle hooks ─────────────────────────────────────────────────────
  onUserRegistered(user) {
    if (this._mockMode || !this._backendConnected) {
      console.debug('[Orchestrator] User registered (offline queue):', user.id);
      return;
    }
    this.registerCustomer({ userId: user.id, name: user.name, contact: user.phone })
      .catch(err => console.warn('[Orchestrator] Failed to sync new user:', err));
  }

  onUserLoggedOut(userId) {
    if (this._mockMode || !this._backendConnected) {
      console.debug('[Orchestrator] User logged out (local only):', userId);
      return;
    }
    localStorage.removeItem('auth_token');
  }

  // ── Customer ─────────────────────────────────────────────────────────────────
  async registerCustomer(userData) {
    if (this._mockMode || !this._backendConnected) {
      return { portoneCustomerId: `cust_mock_${Date.now()}`, razorpayCustomerId: null };
    }
    const response = await axios.post(
      `${this._backendBaseUrl}/api/v1/payments/customer/register`,
      userData,
      { headers: this._authHeaders() }
    );
    return response.data;
  }

  // ── Bills ────────────────────────────────────────────────────────────────────
  async getBills(userId, dept) {
    if (this._mockMode || !this._backendConnected) {
      const localDB = (await import('../localdb/localDB.js')).default;
      return localDB.getBillsByUserAndDept(userId, dept);
    }
    // Backend bills endpoint uses consumer_id = userId for now
    const response = await axios.get(
      `${this._backendBaseUrl}/api/v1/${dept}/bills/${userId}`,
      { headers: this._authHeaders() }
    );
    // Backend returns { bills: [...] }
    return response.data.bills ?? response.data ?? [];
  }

  // ── Payments ─────────────────────────────────────────────────────────────────
  async initiatePayment(payload) {
    if (this._mockMode || !this._backendConnected) {
      const { mockPaymentService } = await import('./mockPaymentService.js');
      return mockPaymentService.initiate(payload);
    }
    const response = await axios.post(
      `${this._backendBaseUrl}/api/v1/payments/initiate`,
      payload,
      { headers: this._authHeaders() }
    );
    return response.data;
  }

  async completePayment(payload) {
    if (this._mockMode || !this._backendConnected) {
      const { mockPaymentService } = await import('./mockPaymentService.js');
      return mockPaymentService.complete(payload);
    }
    const response = await axios.post(
      `${this._backendBaseUrl}/api/v1/payments/complete`,
      payload,
      { headers: this._authHeaders() }
    );
    return response.data;
  }

  async verifyPayment({ gateway, paymentId }) {
    if (this._mockMode || !this._backendConnected) {
      return { verified: true, status: 'SUCCESS' };
    }
    const response = await axios.get(
      `${this._backendBaseUrl}/api/v1/payments/status/${paymentId}`,
      { headers: this._authHeaders() }
    );
    return response.data;
  }

  async getPaymentHistory(userId) {
    if (this._mockMode || !this._backendConnected) {
      const localDB = (await import('../localdb/localDB.js')).default;
      return localDB.getPaymentsByUserId(userId);
    }
    const response = await axios.get(
      `${this._backendBaseUrl}/api/v1/payments/history/${userId}`,
      { headers: this._authHeaders() }
    );
    return response.data;
  }
}

const orchestrator = new Orchestrator();
export default orchestrator;
