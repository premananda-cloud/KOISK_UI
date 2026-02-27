/**
 * MODULE 4 — ORCHESTRATOR (STUB)
 *
 * This is the single connection point between the React app and
 * any real backend. Right now every method is a no-op stub that
 * logs what would be sent.
 *
 * TO CONNECT THE REAL BACKEND:
 *   1. Import your API service here
 *   2. Replace the stub methods with real calls
 *   3. Handle sync queue items from localDB.getPendingSyncItems()
 *   Zero changes to any component or store needed.
 *
 * Events this orchestrator handles:
 *   - onUserRegistered    → POST /api/v1/auth/register
 *   - onUserLoggedOut     → POST /api/v1/auth/logout
 *   - onPaymentRequested  → POST /api/v1/payments/initiate
 *   - onServiceRequest    → POST /api/v1/{dept}/service-requests
 *   - syncPending         → flush localDB syncQueue to backend
 */

class Orchestrator {
  constructor() {
    this._backendConnected = false
    this._backendBaseUrl   = null
  }

  // ── Connection ────────────────────────────────────────────────
  /**
   * Call this when you're ready to connect the real backend.
   * e.g. orchestrator.connect('http://localhost:8000')
   */
  connect(baseUrl) {
    this._backendBaseUrl   = baseUrl
    this._backendConnected = true
    console.info('[Orchestrator] Connected to backend:', baseUrl)
    this.syncPending()
  }

  isConnected() {
    return this._backendConnected
  }

  // ── Auth Events ───────────────────────────────────────────────
  onUserRegistered(user) {
    if (!this._backendConnected) {
      console.debug('[Orchestrator][STUB] User registered locally, will sync later:', user.id)
      return
    }
    // TODO: POST this._backendBaseUrl + '/api/v1/auth/register'
  }

  onUserLoggedOut(userId) {
    if (!this._backendConnected) {
      console.debug('[Orchestrator][STUB] Logout for userId:', userId)
      return
    }
    // TODO: POST this._backendBaseUrl + '/api/v1/auth/logout'
  }

  // ── Payment Events ────────────────────────────────────────────
  onPaymentRequested(paymentData) {
    if (!this._backendConnected) {
      console.debug('[Orchestrator][STUB] Payment requested (mock mode):', paymentData)
      // In mock mode, caller handles payment simulation directly
      return { mode: 'mock' }
    }
    // TODO: POST this._backendBaseUrl + '/api/v1/payments/initiate'
    return { mode: 'real' }
  }

  onPaymentCompleted(paymentData) {
    if (!this._backendConnected) {
      console.debug('[Orchestrator][STUB] Payment completed:', paymentData.id)
      return
    }
    // TODO: POST this._backendBaseUrl + '/api/v1/payments/confirm'
  }

  // ── Service Request Events ────────────────────────────────────
  onServiceRequest(requestData) {
    if (!this._backendConnected) {
      console.debug('[Orchestrator][STUB] Service request queued:', requestData.type)
      return
    }
    // TODO: POST this._backendBaseUrl + `/api/v1/${requestData.dept}/service-requests`
  }

  // ── Sync Queue ────────────────────────────────────────────────
  async syncPending() {
    if (!this._backendConnected) return
    const { localDB } = await import('@/modules/localdb/localDB')
    const pending = await localDB.getPendingSyncItems()
    console.info(`[Orchestrator] Syncing ${pending.length} pending items...`)
    // TODO: iterate pending, push to backend, call localDB.markSynced(item.id)
  }
}

// Singleton — import this anywhere
export const orchestrator = new Orchestrator()
