import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator, KeyboardAvoidingView, Platform,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import axios from "axios";

const BASE_URL = "https://api.cctvplatform.in/api/v1";

export default function LoginScreen({ navigation }: any) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    if (!email || !password) { Alert.alert("Please fill in all fields"); return; }
    setLoading(true);
    try {
      const { data } = await axios.post(`${BASE_URL}/auth/login`, { email, password });
      await AsyncStorage.setItem("access_token", data.access_token);
      await AsyncStorage.setItem("refresh_token", data.refresh_token);
      navigation.replace("Main");
    } catch (e: any) {
      Alert.alert("Login Failed", e.response?.data?.detail || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.container}>
      <Text style={styles.logo}>🎥 CCTV Technician</Text>
      <Text style={styles.subtitle}>Field Service App</Text>

      <TextInput
        style={styles.input}
        placeholder="Email"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoComplete="email"
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />

      <TouchableOpacity style={styles.btn} onPress={handleLogin} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Sign In</Text>}
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 32, backgroundColor: "#f0f4ff" },
  logo: { fontSize: 32, fontWeight: "800", textAlign: "center", marginBottom: 4 },
  subtitle: { textAlign: "center", color: "#6b7280", marginBottom: 40 },
  input: {
    backgroundColor: "#fff", borderRadius: 8, padding: 14,
    marginBottom: 16, fontSize: 16, borderWidth: 1, borderColor: "#d1d5db",
  },
  btn: { backgroundColor: "#2563eb", borderRadius: 8, padding: 16, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
