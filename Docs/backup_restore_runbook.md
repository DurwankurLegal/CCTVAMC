# Database & Cache Backup and Restore Runbook

This runbook outlines the standard operating procedures for taking backups, verifying recovery state, and performing disaster recovery for the PostgreSQL database and Redis cache/broker.

---

## 1. PostgreSQL Backup & Restore

### A. Backup Procedures

To take a complete backup of the PostgreSQL database schemas, tables, and roles, we use `pg_dump` or `pg_dumpall`.

#### 1. Logical Database Dump (Recommended)
This command dumps the `cctvdb` database into a custom-format archive file, which is compressed and allows selective restores of tables or schemas:
```bash
docker exec -t infra-postgres-1 pg_dump -U cctv -F c -b -v -f /var/lib/postgresql/data/cctvdb_backup_$(date +%F).dump cctvdb
```
* `/var/lib/postgresql/data/` maps to the Postgres Docker volume on the host, meaning the backup is written outside the container lifecycle.
* `-F c` specifies the custom directory format (flexible, compressed, readable by `pg_restore`).
* `-b` includes large objects.

#### 2. Plain Text SQL Dump (Schema Only)
Useful for version control or migrations audit:
```bash
docker exec -t infra-postgres-1 pg_dump -U cctv --schema-only -f /var/lib/postgresql/data/cctvdb_schema_$(date +%F).sql cctvdb
```

---

### B. Restore & Recovery Procedures

> [!CAUTION]
> Restoring a database from a dump will overwrite or append to existing data. Make sure you take a snapshot of the current state before initiating a restore.

#### 1. Preparing the Database (Clean Slate)
If you need a completely clean restore, drop and recreate the database:
```bash
docker exec -it infra-postgres-1 psql -U cctv -c "DROP DATABASE IF EXISTS cctvdb;"
docker exec -it infra-postgres-1 psql -U cctv -c "CREATE DATABASE cctvdb WITH OWNER cctv;"
```

#### 2. Restoring from Custom Dump
Use `pg_restore` to restore the schema and data from the `.dump` file:
```bash
docker exec -it infra-postgres-1 pg_restore -U cctv -d cctvdb -v /var/lib/postgresql/data/cctvdb_backup_<YYYY-MM-DD>.dump
```
* `-d cctvdb` specifies the target database.
* `-v` enables verbose log output for tracking progress.

#### 3. Restoring from SQL Plain-Text Dump
```bash
docker exec -it infra-postgres-1 psql -U cctv -d cctvdb -f /var/lib/postgresql/data/cctvdb_backup_<YYYY-MM-DD>.sql
```

---

### C. Manual Verification of Recovery State
After restoring, run the following verification checks:

1. **Verify Table List & Row Counts**:
   ```bash
   docker exec -it infra-postgres-1 psql -U cctv -d cctvdb -c "\dt"
   ```
2. **Verify Row-Level Security Policies**:
   Confirm that RLS remains active on all 34 tenant-scoped tables:
   ```bash
   docker exec -it infra-postgres-1 psql -U cctv -d cctvdb -c "
     SELECT c.relname, c.relrowsecurity 
     FROM pg_class c 
     JOIN pg_namespace n ON n.oid = c.relnamespace 
     WHERE n.nspname = 'public' AND c.relrowsecurity = true;
   "
   ```
3. **Verify Tenant-ID Scoping Check**:
   ```bash
   docker exec -it infra-postgres-1 psql -U cctv -d cctvdb -c "
     SET ROLE rls_check_role;
     SELECT * FROM customers; -- Should block/return zero rows if app.tenant_id is not set
   "
   ```

---

## 2. Redis Snapshotting & Recovery

Redis persists its cache and Celery message queues using RDB (Redis Database) snapshots and AOF (Append Only File) logs.

### A. Manual Backup (Snapshotting)

To force an immediate, synchronous snapshot of the cache memory to disk:
```bash
docker exec -it infra-redis-1 redis-cli -a redis_dev_pass SAVE
```
* This writes the current snapshot to the `dump.rdb` file.
* For non-blocking background snapshotting, use `BGSAVE` instead:
  ```bash
  docker exec -it infra-redis-1 redis-cli -a redis_dev_pass BGSAVE
  ```
  Check snapshot progress using:
  ```bash
  docker exec -it infra-redis-1 redis-cli -a redis_dev_pass LASTSAVE
  ```

---

### B. Restore & Disaster Recovery

Redis automatically loads the `dump.rdb` file from its working directory on startup.

#### 1. Retrieve the Redis Data Directory Path
```bash
docker exec -it infra-redis-1 redis-cli -a redis_dev_pass config get dir
```

#### 2. Restore Steps
1. Stop the Redis container:
   ```bash
   docker compose stop redis
   ```
2. Copy your backup `dump.rdb` file into the Redis volume mount path on the host system (configured under `infra/docker-compose.yml` or standard volume directory).
3. Start the Redis container:
   ```bash
   docker compose start redis
   ```
4. Verify that data has loaded successfully:
   ```bash
   docker exec -it infra-redis-1 redis-cli -a redis_dev_pass ping
   # Output should be PONG
   docker exec -it infra-redis-1 redis-cli -a redis_dev_pass info persistence
   # Verify 'loading:0' and check 'rdb_last_save_time'
   ```
