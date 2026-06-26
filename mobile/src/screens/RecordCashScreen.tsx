import React, { useState, useEffect } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, Alert,
  ScrollView, TextInput, ActivityIndicator, Image
} from "react-native";
import { launchCamera } from "react-native-image-picker";
import NetInfo from "@react-native-netinfo";
import apiClient from "../services/apiClient";
import { queueForSync } from "../db/localDb";

interface Company {
  id: string;
  name: string;
  is_default: boolean;
}

export default function RecordCashScreen({ route, navigation }: any) {
  const [customerName, setCustomerName] = useState("");
  const [amount, setAmount] = useState("");
  const [remarks, setRemarks] = useState("");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [serviceTicketId, setServiceTicketId] = useState<string | null>(null);
  const [invoiceId, setInvoiceId] = useState<string | null>(null);
  
  const [receiptPhotoUri, setReceiptPhotoUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchingCompanies, setFetchingCompanies] = useState(false);

  useEffect(() => {
    async function loadCompanies() {
      setFetchingCompanies(true);
      try {
        const netState = await NetInfo.fetch();
        let loadedCompanies: Company[] = [];
        if (netState.isConnected) {
          const { data } = await apiClient.get<Company[]>("/companies");
          loadedCompanies = data;
          setCompanies(data);
        } else {
          // Offline fallback
          loadedCompanies = [
            { id: "fallback-default", name: "Default Company", is_default: true }
          ];
          setCompanies(loadedCompanies);
        }

        // Handle route parameters context pre-population
        const ticket = route?.params?.ticket;
        const invoice = route?.params?.invoice;

        if (ticket) {
          setServiceTicketId(ticket.id);
          setRemarks(`Collected for Ticket #${ticket.ticket_number}`);
          if (ticket.company_id) {
            setSelectedCompanyId(ticket.company_id);
          } else {
            const defaultComp = loadedCompanies.find(c => c.is_default);
            if (defaultComp) setSelectedCompanyId(defaultComp.id);
            else if (loadedCompanies.length > 0) setSelectedCompanyId(loadedCompanies[0].id);
          }

          if (netState.isConnected && ticket.customer_id) {
            try {
              const { data: cust } = await apiClient.get(`/customers/${ticket.customer_id}`);
              if (cust?.name) {
                setCustomerName(cust.name);
              }
            } catch (err) {
              console.warn("Failed to fetch customer name", err);
            }
          }
        } else if (invoice) {
          setInvoiceId(invoice.id);
          setRemarks(`Collected for Invoice #${invoice.invoice_number}`);
          if (invoice.company_id) {
            setSelectedCompanyId(invoice.company_id);
          } else {
            const defaultComp = loadedCompanies.find(c => c.is_default);
            if (defaultComp) setSelectedCompanyId(defaultComp.id);
            else if (loadedCompanies.length > 0) setSelectedCompanyId(loadedCompanies[0].id);
          }
          if (invoice.customer_name) {
            setCustomerName(invoice.customer_name);
          }
        } else {
          // Default selection if no context passed
          const defaultComp = loadedCompanies.find(c => c.is_default);
          if (defaultComp) {
            setSelectedCompanyId(defaultComp.id);
          } else if (loadedCompanies.length > 0) {
            setSelectedCompanyId(loadedCompanies[0].id);
          }
        }
      } catch (e) {
        console.warn("Failed to load companies/context", e);
        setCompanies([
          { id: "fallback-default", name: "Default Company", is_default: true }
        ]);
        setSelectedCompanyId("fallback-default");
      } finally {
        setFetchingCompanies(false);
      }
    }
    loadCompanies();
  }, [route?.params]);

  async function handleCapturePhoto() {
    launchCamera({ mediaType: "photo", quality: 0.8 }, (resp) => {
      if (!resp.assets?.[0]) return;
      setReceiptPhotoUri(resp.assets[0].uri!);
    });
  }

  async function handleSubmit() {
    if (!customerName || !amount || !selectedCompanyId) {
      Alert.alert("Error", "Please fill in all mandatory fields (Customer, Company, Amount)");
      return;
    }

    const amtNum = parseFloat(amount);
    if (isNaN(amtNum) || amtNum <= 0) {
      Alert.alert("Error", "Please enter a valid amount greater than 0");
      return;
    }

    setLoading(true);
    try {
      const netState = await NetInfo.fetch();
      const payload = {
        customer_name: customerName,
        company_id: selectedCompanyId,
        service_ticket_id: serviceTicketId || null,
        invoice_id: invoiceId || null,
        amount: amtNum,
        collected_at: new Date().toISOString(),
        remarks: remarks || "",
        local_photo_path: receiptPhotoUri || null,
        receipt_photo_url: null // Set to null, syncManager will handle upload if local_photo_path is set
      };

      if (netState.isConnected) {
        // Online path: create record via API directly
        const { data } = await apiClient.post("/cash-collections", {
          customer_name: payload.customer_name,
          company_id: payload.company_id,
          service_ticket_id: payload.service_ticket_id,
          invoice_id: payload.invoice_id,
          amount: payload.amount,
          collected_at: payload.collected_at,
          remarks: payload.remarks
        });

        // If photo exists, upload it directly
        if (receiptPhotoUri && data?.id) {
          const formData = new FormData();
          formData.append("file", {
            uri: receiptPhotoUri,
            type: "image/jpeg",
            name: `receipt_${data.id}.jpg`
          } as any);

          await apiClient.post(`/cash-collections/${data.id}/media`, formData, {
            headers: { "Content-Type": "multipart/form-data" }
          });
        }
        Alert.alert("Success", "Cash entry submitted successfully.");
      } else {
        // Offline path: queue in local db
        await queueForSync("cash_collection_create", payload);
        Alert.alert("Saved Offline", "Your cash entry has been saved locally and will sync once internet is restored.");
      }
      navigation.goBack();
    } catch (e: any) {
      Alert.alert("Submission Failed", e.response?.data?.detail || e.message || "Error submitting entry");
    } finally {
      setLoading(false);
    }
  }

  if (loading || fetchingCompanies) {
    return <ActivityIndicator style={styles.center} size="large" color="#2563eb" />;
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.heading}>💵 Record Cash Collection</Text>
      <Text style={styles.subtitle}>Enter cash collected directly from customer</Text>

      <Text style={styles.label}>Customer Name *</Text>
      <TextInput
        style={styles.input}
        placeholder="Customer Name"
        value={customerName}
        onChangeText={setCustomerName}
      />

      <Text style={styles.label}>Operating Company *</Text>
      <View style={styles.pickerContainer}>
        {companies.map((c) => (
          <TouchableOpacity
            key={c.id}
            style={[
              styles.companyChip,
              selectedCompanyId === c.id && styles.selectedChip
            ]}
            onPress={() => setSelectedCompanyId(c.id)}
          >
            <Text style={[
              styles.chipText,
              selectedCompanyId === c.id && styles.selectedChipText
            ]}>
              {c.name} {c.is_default ? "(Default)" : ""}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Amount Received (INR) *</Text>
      <TextInput
        style={styles.input}
        placeholder="e.g. 500.00"
        value={amount}
        onChangeText={setAmount}
        keyboardType="numeric"
      />

      <Text style={styles.label}>Remarks</Text>
      <TextInput
        style={[styles.input, styles.textArea]}
        placeholder="Additional comments (optional)..."
        value={remarks}
        onChangeText={setRemarks}
        multiline
        numberOfLines={3}
      />

      <Text style={styles.label}>Receipt Photo (Optional)</Text>
      {receiptPhotoUri ? (
        <View style={styles.photoContainer}>
          <Image source={{ uri: receiptPhotoUri }} style={styles.photoPreview} />
          <TouchableOpacity style={styles.btnDanger} onPress={() => setReceiptPhotoUri(null)}>
            <Text style={styles.btnText}>Remove Photo</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <TouchableOpacity style={styles.btnSecondary} onPress={handleCapturePhoto}>
          <Text style={styles.btnText}>📸 Capture Receipt Photo</Text>
        </TouchableOpacity>
      )}

      <TouchableOpacity style={styles.btnPrimary} onPress={handleSubmit}>
        <Text style={styles.btnText}>Submit Cash Entry</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc", padding: 16 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  heading: { fontSize: 20, fontWeight: "700", color: "#1e293b", marginBottom: 4 },
  subtitle: { color: "#64748b", marginBottom: 20, fontSize: 13 },
  label: { fontWeight: "600", color: "#334155", marginTop: 12, marginBottom: 6 },
  input: {
    backgroundColor: "#fff", borderRadius: 8, padding: 12,
    fontSize: 15, borderWidth: 1, borderColor: "#cbd5e1",
    color: "#0f172a"
  },
  textArea: { minHeight: 80, textAlignVertical: "top" },
  pickerContainer: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginVertical: 4 },
  companyChip: {
    backgroundColor: "#e2e8f0", paddingVertical: 8, paddingHorizontal: 12,
    borderRadius: 20, borderWidth: 1, borderColor: "#cbd5e1"
  },
  selectedChip: { backgroundColor: "#2563eb", borderColor: "#2563eb" },
  chipText: { color: "#475569", fontWeight: "600", fontSize: 13 },
  selectedChipText: { color: "#fff" },
  photoContainer: { alignItems: "center", marginVertical: 10 },
  photoPreview: { width: "100%", height: 180, borderRadius: 8, objectFit: "contain", marginBottom: 8 },
  btnPrimary: { backgroundColor: "#2563eb", borderRadius: 8, padding: 16, alignItems: "center", marginTop: 24, marginBottom: 40 },
  btnSecondary: { backgroundColor: "#475569", borderRadius: 8, padding: 12, alignItems: "center", marginVertical: 8 },
  btnDanger: { backgroundColor: "#ef4444", borderRadius: 8, padding: 8, width: 120, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 14 }
});
