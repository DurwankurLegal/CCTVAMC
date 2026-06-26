/**
 * Engineer Visit Detail Screen — handles the full field workflow:
 *   Create visit → Check-in (GPS) → Capture photos → Checkout with parts + signature
 * All actions queue locally if offline; sync manager uploads on reconnect.
 */
import React, { useState, useRef } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, Alert,
  ScrollView, TextInput, ActivityIndicator,
} from "react-native";
import { launchCamera } from "react-native-image-picker";
import SignatureCanvas from "react-native-signature-canvas";
import NetInfo from "@react-native-netinfo";
import { getCurrentLocation, requestLocationPermission } from "../services/locationService";
import { queueForSync, saveLocalVisit } from "../db/localDb";
import apiClient from "../services/apiClient";

interface Props { route: any; navigation: any }

export default function VisitDetailScreen({ route, navigation }: Props) {
  const { ticket } = route.params;
  const [visitId, setVisitId] = useState<string | null>(null);
  const [checkedIn, setCheckedIn] = useState(false);
  const [workPerformed, setWorkPerformed] = useState("");
  const [photoPaths, setPhotoPaths] = useState<string[]>([]);
  const [signatureRef] = useState(useRef<any>(null));
  const [loading, setLoading] = useState(false);

  async function handleCreateAndCheckin() {
    setLoading(true);
    try {
      const hasPermission = await requestLocationPermission();
      if (!hasPermission) { Alert.alert("Location permission required"); return; }

      const coords = await getCurrentLocation();
      const netState = await NetInfo.fetch();

      if (netState.isConnected) {
        // Online path: create visit + check in via API
        const { data: visit } = await apiClient.post("/engineer-visits", {
          ticket_id: ticket.id,
          visit_type: "corrective",
        });
        await apiClient.post(`/engineer-visits/${visit.id}/checkin`, {
          lat: coords.lat,
          lng: coords.lng,
        });
        setVisitId(visit.id);
      } else {
        // Offline path: create a local ID and queue for sync
        const localId = `local_${Date.now()}`;
        await saveLocalVisit({
          id: localId,
          ticket_id: ticket.id,
          visit_type: "corrective",
          checkin_at: new Date().toISOString(),
          checkin_lat: coords.lat,
          checkin_lng: coords.lng,
        });
        await queueForSync("engineer_visit_checkin", { visit_id: localId, lat: coords.lat, lng: coords.lng });
        setVisitId(localId);
        Alert.alert("Offline", "Check-in saved locally. Will sync when back online.");
      }
      setCheckedIn(true);
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCapturePhoto() {
    launchCamera({ mediaType: "photo", quality: 0.8 }, async (resp) => {
      if (!resp.assets?.[0]) return;
      const uri = resp.assets[0].uri!;
      setPhotoPaths((prev) => [...prev, uri]);
      if (visitId) {
        await queueForSync("media_upload", {
          visit_id: visitId,
          file_uri: uri,
          type: "photo",
        });
      }
    });
  }

  async function handleCheckout() {
    if (!visitId) return;
    setLoading(true);
    try {
      const coords = await getCurrentLocation();
      const signature = await signatureRef.current?.readSignature();
      if (signature) {
        await queueForSync("media_upload", {
          visit_id: visitId,
          file_uri: signature,
          type: "signature",
        });
      }

      const netState = await NetInfo.fetch();
      const checkoutPayload = {
        lat: coords.lat,
        lng: coords.lng,
        work_performed: workPerformed,
        parts_used: [],
      };

      if (netState.isConnected) {
        await apiClient.post(`/engineer-visits/${visitId}/checkout`, checkoutPayload);
      } else {
        await queueForSync("engineer_visit_checkout", { visit_id: visitId, ...checkoutPayload });
        Alert.alert("Offline", "Checkout saved locally. Will sync when back online.");
      }
      navigation.goBack();
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <ActivityIndicator style={styles.center} size="large" color="#2563eb" />;

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.heading}>Ticket: {ticket.ticket_number}</Text>
      <Text style={styles.complaint}>{ticket.complaint}</Text>

      {!checkedIn ? (
        <TouchableOpacity style={styles.btnPrimary} onPress={handleCreateAndCheckin}>
          <Text style={styles.btnText}>📍 Check In</Text>
        </TouchableOpacity>
      ) : (
        <>
          <Text style={styles.sectionLabel}>Work Performed</Text>
          <TextInput
            style={styles.textArea}
            multiline
            numberOfLines={4}
            value={workPerformed}
            onChangeText={setWorkPerformed}
            placeholder="Describe the work done..."
          />

          <TouchableOpacity style={styles.btnSecondary} onPress={handleCapturePhoto}>
            <Text style={styles.btnText}>📸 Capture Photo ({photoPaths.length})</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.btnSecondary, { backgroundColor: "#047857" }]}
            onPress={() => navigation.navigate("RecordCash", { ticket })}
          >
            <Text style={styles.btnText}>💵 Record Cash Payment</Text>
          </TouchableOpacity>

          <Text style={styles.sectionLabel}>Customer Signature</Text>
          <View style={styles.signatureBox}>
            <SignatureCanvas
              ref={signatureRef}
              onOK={() => {}}
              webStyle=".m-signature-pad--footer { display: none; }"
            />
          </View>

          <TouchableOpacity
            style={[styles.btnPrimary, !workPerformed && styles.disabled]}
            onPress={handleCheckout}
            disabled={!workPerformed}
          >
            <Text style={styles.btnText}>✅ Check Out & Submit</Text>
          </TouchableOpacity>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb", padding: 16 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  heading: { fontSize: 18, fontWeight: "700", color: "#1e3a5f", marginBottom: 8 },
  complaint: { color: "#374151", marginBottom: 16 },
  sectionLabel: { fontWeight: "600", color: "#374151", marginTop: 16, marginBottom: 8 },
  textArea: {
    borderWidth: 1, borderColor: "#d1d5db", borderRadius: 8,
    padding: 12, backgroundColor: "#fff", minHeight: 100,
    textAlignVertical: "top",
  },
  signatureBox: { height: 200, borderWidth: 1, borderColor: "#d1d5db", borderRadius: 8, marginBottom: 16, overflow: "hidden" },
  btnPrimary: { backgroundColor: "#2563eb", borderRadius: 8, padding: 16, alignItems: "center", marginBottom: 12 },
  btnSecondary: { backgroundColor: "#6b7280", borderRadius: 8, padding: 14, alignItems: "center", marginBottom: 12 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  disabled: { opacity: 0.5 },
});
