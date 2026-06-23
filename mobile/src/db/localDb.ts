/**
 * SQLite local database for offline-first operation.
 * Stores tickets, visits and sync queue while device is offline.
 */
import SQLite from "react-native-sqlite-storage";

SQLite.enablePromise(true);

let db: SQLite.SQLiteDatabase | null = null;

export async function getDb(): Promise<SQLite.SQLiteDatabase> {
  if (db) return db;
  db = await SQLite.openDatabase({ name: "cctv_tech.db", location: "default" });
  await initSchema(db);
  return db;
}

async function initSchema(db: SQLite.SQLiteDatabase) {
  await db.executeSql(`
    CREATE TABLE IF NOT EXISTS sync_queue (
      id              TEXT PRIMARY KEY,
      entity_type     TEXT NOT NULL,
      payload         TEXT NOT NULL,
      created_at      TEXT NOT NULL,
      synced          INTEGER DEFAULT 0,
      status          TEXT DEFAULT 'pending',
      retry_count     INTEGER DEFAULT 0,
      last_error      TEXT,
      last_attempt_at TEXT
    )
  `);
  // Idempotent column adds for devices created before these columns existed.
  // SQLite has no ADD COLUMN IF NOT EXISTS, so swallow "duplicate column" errors.
  for (const col of [
    "status TEXT DEFAULT 'pending'",
    "retry_count INTEGER DEFAULT 0",
    "last_error TEXT",
    "last_attempt_at TEXT",
  ]) {
    try {
      await db.executeSql(`ALTER TABLE sync_queue ADD COLUMN ${col}`);
    } catch (e) {
      // column already exists — ignore
    }
  }

  await db.executeSql(`
    CREATE TABLE IF NOT EXISTS local_visits (
      id              TEXT PRIMARY KEY,
      ticket_id       TEXT,
      amc_contract_id TEXT,
      visit_type      TEXT DEFAULT 'corrective',
      checkin_at      TEXT,
      checkout_at     TEXT,
      checkin_lat     REAL,
      checkin_lng     REAL,
      checkout_lat    REAL,
      checkout_lng    REAL,
      work_performed  TEXT,
      parts_used      TEXT DEFAULT '[]',
      photo_paths     TEXT DEFAULT '[]',
      signature_path  TEXT,
      synced          INTEGER DEFAULT 0
    )
  `);

  await db.executeSql(`
    CREATE TABLE IF NOT EXISTS local_tickets (
      id            TEXT PRIMARY KEY,
      ticket_number TEXT,
      customer_name TEXT,
      status        TEXT,
      priority      TEXT,
      complaint     TEXT,
      synced_at     TEXT
    )
  `);
}

export async function queueForSync(entityType: string, payload: object) {
  const db = await getDb();
  const id = `${entityType}_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  await db.executeSql(
    "INSERT INTO sync_queue (id, entity_type, payload, created_at) VALUES (?, ?, ?, ?)",
    [id, entityType, JSON.stringify(payload), new Date().toISOString()]
  );
  return id;
}

// Stop retrying after this many failures so a permanently-bad item doesn't loop.
export const MAX_SYNC_RETRIES = 5;

export async function getPendingQueue(): Promise<any[]> {
  const db = await getDb();
  // Skip items that have exhausted their retries (status = 'failed').
  const [result] = await db.executeSql(
    "SELECT * FROM sync_queue WHERE synced = 0 AND status != 'failed' ORDER BY created_at ASC"
  );
  return Array.from({ length: result.rows.length }, (_, i) => result.rows.item(i));
}

export async function markSynced(id: string) {
  const db = await getDb();
  await db.executeSql(
    "UPDATE sync_queue SET synced = 1, status = 'synced', last_attempt_at = ? WHERE id = ?",
    [new Date().toISOString(), id]
  );
}

/** Record a failed sync attempt; flips to terminal 'failed' after MAX_SYNC_RETRIES
 *  so the item stays visible (not silently lost) for supervisor review. */
export async function markFailed(id: string, error: string) {
  const db = await getDb();
  const [r] = await db.executeSql("SELECT retry_count FROM sync_queue WHERE id = ?", [id]);
  const retries = (r.rows.length ? r.rows.item(0).retry_count : 0) + 1;
  const status = retries >= MAX_SYNC_RETRIES ? "failed" : "retrying";
  await db.executeSql(
    "UPDATE sync_queue SET retry_count = ?, last_error = ?, last_attempt_at = ?, status = ? WHERE id = ?",
    [retries, String(error).slice(0, 500), new Date().toISOString(), status, id]
  );
}

/** Aggregate counts for the sync-status screen. */
export async function getQueueStats(): Promise<{ pending: number; retrying: number; failed: number; synced: number }> {
  const db = await getDb();
  const [r] = await db.executeSql(
    `SELECT
       SUM(CASE WHEN synced = 0 AND status = 'pending'  THEN 1 ELSE 0 END) AS pending,
       SUM(CASE WHEN synced = 0 AND status = 'retrying' THEN 1 ELSE 0 END) AS retrying,
       SUM(CASE WHEN synced = 0 AND status = 'failed'   THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN synced = 1 THEN 1 ELSE 0 END) AS synced
     FROM sync_queue`
  );
  const row = r.rows.item(0);
  return {
    pending: row.pending || 0, retrying: row.retrying || 0,
    failed: row.failed || 0, synced: row.synced || 0,
  };
}

/** All queue items (newest first) for the sync-status screen. */
export async function getAllQueueItems(): Promise<any[]> {
  const db = await getDb();
  const [result] = await db.executeSql("SELECT * FROM sync_queue ORDER BY created_at DESC");
  return Array.from({ length: result.rows.length }, (_, i) => result.rows.item(i));
}

/** Reset a failed item so the user can retry it manually. */
export async function retryFailed(id: string) {
  const db = await getDb();
  await db.executeSql(
    "UPDATE sync_queue SET status = 'pending', retry_count = 0, last_error = NULL WHERE id = ?",
    [id]
  );
}

/** When a locally-created visit gets a real server id, rewrite that id in every
 *  still-pending queue payload (checkout, media, parts) so follow-up actions
 *  target the server record instead of the local placeholder. */
export async function remapVisitId(localId: string, serverId: string) {
  const db = await getDb();
  const [result] = await db.executeSql(
    "SELECT id, payload FROM sync_queue WHERE synced = 0 AND payload LIKE ?",
    [`%${localId}%`]
  );
  for (let i = 0; i < result.rows.length; i++) {
    const item = result.rows.item(i);
    const updated = item.payload.split(localId).join(serverId);
    await db.executeSql("UPDATE sync_queue SET payload = ? WHERE id = ?", [updated, item.id]);
  }
}

export async function saveLocalVisit(visit: object & { id: string }) {
  const db = await getDb();
  const v = visit as any;
  await db.executeSql(
    `INSERT OR REPLACE INTO local_visits
     (id, ticket_id, amc_contract_id, visit_type, checkin_at, checkout_at,
      checkin_lat, checkin_lng, checkout_lat, checkout_lng,
      work_performed, parts_used, photo_paths, signature_path, synced)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
    [
      v.id, v.ticket_id, v.amc_contract_id, v.visit_type,
      v.checkin_at, v.checkout_at,
      v.checkin_lat, v.checkin_lng, v.checkout_lat, v.checkout_lng,
      v.work_performed, JSON.stringify(v.parts_used || []),
      JSON.stringify(v.photo_paths || []), v.signature_path, 0,
    ]
  );
}
