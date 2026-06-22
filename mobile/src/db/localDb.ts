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
      id          TEXT PRIMARY KEY,
      entity_type TEXT NOT NULL,
      payload     TEXT NOT NULL,
      created_at  TEXT NOT NULL,
      synced      INTEGER DEFAULT 0
    )
  `);

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

export async function getPendingQueue(): Promise<any[]> {
  const db = await getDb();
  const [result] = await db.executeSql(
    "SELECT * FROM sync_queue WHERE synced = 0 ORDER BY created_at ASC"
  );
  return Array.from({ length: result.rows.length }, (_, i) => result.rows.item(i));
}

export async function markSynced(id: string) {
  const db = await getDb();
  await db.executeSql("UPDATE sync_queue SET synced = 1 WHERE id = ?", [id]);
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
