/**
 * MODULE 3 — LOCAL USER DATABASE
 *
 * Uses IndexedDB (via the `idb` wrapper) for persistent local storage.
 * This is the source of truth for the demo and the sync source when
 * the real backend is connected through the Orchestrator (Module 4).
 *
 * Stores: users, sessions, serviceRequests, syncQueue
 */

import { openDB } from 'idb'

const DB_NAME    = 'koisk_local'
const DB_VERSION = 1

let _db = null

export const localDB = {
  // ── Init ──────────────────────────────────────────────────────────
  async init() {
    if (_db) return _db
    _db = await openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        // Users store
        if (!db.objectStoreNames.contains('users')) {
          const users = db.createObjectStore('users', { keyPath: 'id' })
          users.createIndex('byPhone', 'phone', { unique: true })
        }

        // Sessions store (active login tokens)
        if (!db.objectStoreNames.contains('sessions')) {
          db.createObjectStore('sessions', { keyPath: 'userId' })
        }

        // Service requests (pre-seeded demo data + new requests)
        if (!db.objectStoreNames.contains('serviceRequests')) {
          const reqs = db.createObjectStore('serviceRequests', { keyPath: 'id' })
          reqs.createIndex('byUserId', 'userId')
        }

        // Sync queue — records waiting to push to real backend
        if (!db.objectStoreNames.contains('syncQueue')) {
          const sq = db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true })
          sq.createIndex('bySynced', 'synced')
        }
      },
    })

    // Seed demo data on first run
    await localDB._seedDemoData()
    return _db
  },

  // ── Users ─────────────────────────────────────────────────────────
  async createUser(userData) {
    const db = await localDB.init()
    await db.add('users', userData)
    await localDB._addToSyncQueue('CREATE_USER', userData)
    return userData
  },

  async getUserByPhone(phone) {
    const db = await localDB.init()
    return db.getFromIndex('users', 'byPhone', phone)
  },

  async getUserById(id) {
    const db = await localDB.init()
    return db.get('users', id)
  },

  async updateUser(userData) {
    const db = await localDB.init()
    await db.put('users', userData)
    await localDB._addToSyncQueue('UPDATE_USER', userData)
    return userData
  },

  // ── Sessions ──────────────────────────────────────────────────────
  async saveSession(userId, sessionData) {
    const db = await localDB.init()
    return db.put('sessions', { userId, ...sessionData, savedAt: Date.now() })
  },

  async getSession(userId) {
    const db = await localDB.init()
    return db.get('sessions', userId)
  },

  async clearSession(userId) {
    const db = await localDB.init()
    return db.delete('sessions', userId)
  },

  // ── Service Requests ──────────────────────────────────────────────
  async getRequestsByUser(userId) {
    const db = await localDB.init()
    return db.getAllFromIndex('serviceRequests', 'byUserId', userId)
  },

  async createRequest(requestData) {
    const db = await localDB.init()
    await db.add('serviceRequests', requestData)
    await localDB._addToSyncQueue('CREATE_REQUEST', requestData)
    return requestData
  },

  // ── Sync Queue ────────────────────────────────────────────────────
  async _addToSyncQueue(action, payload) {
    const db = await localDB.init()
    return db.add('syncQueue', {
      action,
      payload,
      synced: false,
      createdAt: Date.now(),
    })
  },

  async getPendingSyncItems() {
    const db = await localDB.init()
    return db.getAllFromIndex('syncQueue', 'bySynced', false)
  },

  async markSynced(id) {
    const db = await localDB.init()
    const item = await db.get('syncQueue', id)
    if (item) {
      item.synced = true
      item.syncedAt = Date.now()
      await db.put('syncQueue', item)
    }
  },

  // ── Demo Seed Data ────────────────────────────────────────────────
  /**
   * Seeds one pre-built citizen profile so the demo always starts
   * in a known, realistic state. Uses a stable ID so it only seeds once.
   */
  async _seedDemoData() {
    const db = await localDB.init()

    const DEMO_USER_ID   = 'demo-user-ramesh-kumar-001'
    const existing = await db.get('users', DEMO_USER_ID)
    if (existing) return // Already seeded

    const demoUser = {
      id:         DEMO_USER_ID,
      name:       'Ramesh Kumar',
      phone:      '9876543210',
      // PIN: 1234 — stored as plain string for demo only
      // In production: bcrypt hash
      pinHash:    '1234',
      consumerId: 'ELEC-MH-00234',
      language:   'en',
      isDemo:     true,
      syncedToBackend: false,
      createdAt:  new Date('2026-01-10T08:00:00Z').toISOString(),
    }

    const demoRequests = [
      {
        id:        'req-demo-001',
        userId:    DEMO_USER_ID,
        type:      'ELECTRICITY_BILL',
        dept:      'electricity',
        status:    'COMPLETED',
        amount:    1847,
        billMonth: '2026-01',
        reference: 'PAY-ELEC-20260125',
        createdAt: '2026-01-25T10:30:00Z',
      },
      {
        id:        'req-demo-002',
        userId:    DEMO_USER_ID,
        type:      'WATER_LEAK_COMPLAINT',
        dept:      'water',
        status:    'IN_PROGRESS',
        amount:    null,
        location:  'Near main gate, Block B',
        reference: 'COMP-WAT-20260222',
        createdAt: '2026-02-22T14:15:00Z',
      },
      {
        id:        'req-demo-003',
        userId:    DEMO_USER_ID,
        type:      'GAS_NEW_CONNECTION',
        dept:      'gas',
        status:    'APPROVED',
        amount:    2500,
        reference: 'GAS-CONN-20260218',
        createdAt: '2026-02-18T09:00:00Z',
      },
      {
        id:        'req-demo-004',
        userId:    DEMO_USER_ID,
        type:      'WATER_BILL',
        dept:      'water',
        status:    'PENDING',
        amount:    340,
        billMonth: '2026-02',
        reference: 'BILL-WAT-20260201',
        dueDate:   '2026-03-05',
        createdAt: '2026-02-01T08:00:00Z',
      },
    ]

    await db.add('users', demoUser)
    for (const req of demoRequests) {
      await db.add('serviceRequests', req)
    }
  },
}
