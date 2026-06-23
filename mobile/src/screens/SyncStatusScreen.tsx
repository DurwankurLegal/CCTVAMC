import React, { useState, useEffect, useCallback } from "react";
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, RefreshControl,
} from "react-native";
import {
  getQueueStats, getAllQueueItems, retryFailed, MAX_SYNC_RETRIES,
} from "../db/localDb";
import { processSyncQueue } from "../services/syncManager";

const STATUS_COLOR: Record<string, string> = {
  pending: "#2563eb", retrying: "#d97706", failed: "#dc2626", synced: "#16a34a",
};

export default function SyncStatusScreen() {
  const [stats, setStats] = useState({ pending: 0, retrying: 0, failed: 0, synced: 0 });
  const [items, setItems] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setStats(await getQueueStats());
    setItems(await getAllQueueItems());
  }, []);

  useEffect(() => { load(); }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try { await processSyncQueue(); } catch { /* errors are recorded per-item */ }
    await load();
    setRefreshing(false);
  }, [load]);

  const onRetry = useCallback(async (id: string) => {
    await retryFailed(id);
    await processSyncQueue().catch(() => undefined);
    await load();
  }, [load]);

  return (
    <View style={styles.container}>
      <View style={styles.statsRow}>
        {(["pending", "retrying", "failed", "synced"] as const).map((k) => (
          <View key={k} style={styles.statCard}>
            <Text style={[styles.statNum, { color: STATUS_COLOR[k] }]}>{stats[k]}</Text>
            <Text style={styles.statLabel}>{k}</Text>
          </View>
        ))}
      </View>

      <FlatList
        data={items}
        keyExtractor={(i) => i.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={<Text style={styles.empty}>Nothing queued. Pull down to sync.</Text>}
        renderItem={({ item }) => {
          const status = item.synced ? "synced" : item.status || "pending";
          return (
            <View style={styles.item}>
              <View style={{ flex: 1 }}>
                <Text style={styles.entity}>{item.entity_type}</Text>
                <Text style={styles.meta}>{new Date(item.created_at).toLocaleString()}</Text>
                {!!item.last_error && <Text style={styles.error} numberOfLines={2}>⚠ {item.last_error}</Text>}
                {item.retry_count > 0 && (
                  <Text style={styles.meta}>retries: {item.retry_count}/{MAX_SYNC_RETRIES}</Text>
                )}
              </View>
              <View style={{ alignItems: "flex-end" }}>
                <Text style={[styles.badge, { color: STATUS_COLOR[status] }]}>{status}</Text>
                {status === "failed" && (
                  <TouchableOpacity onPress={() => onRetry(item.id)}>
                    <Text style={styles.retry}>Retry</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  statsRow: { flexDirection: "row", padding: 12, gap: 8 },
  statCard: { flex: 1, backgroundColor: "#fff", borderRadius: 8, padding: 12, alignItems: "center", borderWidth: 1, borderColor: "#e5e7eb" },
  statNum: { fontSize: 22, fontWeight: "800" },
  statLabel: { fontSize: 12, color: "#6b7280", textTransform: "capitalize" },
  item: { flexDirection: "row", backgroundColor: "#fff", marginHorizontal: 12, marginVertical: 4, padding: 12, borderRadius: 8, borderWidth: 1, borderColor: "#e5e7eb" },
  entity: { fontWeight: "700", fontSize: 14 },
  meta: { fontSize: 12, color: "#6b7280", marginTop: 2 },
  error: { fontSize: 12, color: "#dc2626", marginTop: 4 },
  badge: { fontWeight: "700", textTransform: "uppercase", fontSize: 12 },
  retry: { color: "#2563eb", fontWeight: "700", marginTop: 8 },
  empty: { textAlign: "center", color: "#9ca3af", marginTop: 60 },
});
