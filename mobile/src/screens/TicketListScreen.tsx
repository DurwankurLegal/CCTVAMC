import React, { useEffect, useState } from "react";
import {
  View, Text, FlatList, TouchableOpacity,
  StyleSheet, ActivityIndicator, RefreshControl,
} from "react-native";
import apiClient from "../services/apiClient";

interface Ticket {
  id: string;
  ticket_number: string;
  customer_id: string;
  status: string;
  priority: string;
  complaint: string;
  sla_breached: boolean;
}

const PRIORITY_COLOR: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#d97706",
  low: "#16a34a",
};

export default function TicketListScreen({ navigation }: any) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  async function fetchTickets() {
    try {
      const { data } = await apiClient.get("/service-tickets?limit=100");
      setTickets(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => { fetchTickets(); }, []);

  if (loading) return <ActivityIndicator style={styles.center} size="large" color="#2563eb" />;

  return (
    <FlatList
      data={tickets}
      keyExtractor={(t) => t.id}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchTickets(); }} />}
      renderItem={({ item }) => (
        <TouchableOpacity
          style={[styles.card, item.sla_breached && styles.breached]}
          onPress={() => navigation.navigate("VisitDetail", { ticket: item })}
        >
          <View style={styles.row}>
            <Text style={styles.ticketNo}>{item.ticket_number}</Text>
            <View style={[styles.badge, { backgroundColor: PRIORITY_COLOR[item.priority] || "#6b7280" }]}>
              <Text style={styles.badgeText}>{item.priority.toUpperCase()}</Text>
            </View>
          </View>
          <Text style={styles.complaint} numberOfLines={2}>{item.complaint}</Text>
          <Text style={styles.status}>Status: {item.status.replace("_", " ")}</Text>
          {item.sla_breached && <Text style={styles.slaWarn}>⚠ SLA Breached</Text>}
        </TouchableOpacity>
      )}
      contentContainerStyle={{ padding: 16 }}
    />
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  card: { backgroundColor: "#fff", borderRadius: 8, padding: 16, marginBottom: 12, elevation: 2 },
  breached: { borderLeftWidth: 4, borderLeftColor: "#dc2626" },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  ticketNo: { fontWeight: "700", fontSize: 15, color: "#1e3a5f" },
  badge: { borderRadius: 4, paddingHorizontal: 8, paddingVertical: 2 },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "700" },
  complaint: { color: "#374151", marginBottom: 6 },
  status: { color: "#6b7280", fontSize: 12 },
  slaWarn: { color: "#dc2626", fontWeight: "700", marginTop: 4 },
});
