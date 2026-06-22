import React, { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import AppNavigator from "./src/navigation/AppNavigator";
import { startSyncListener } from "./src/services/syncManager";

export default function App() {
  useEffect(() => {
    startSyncListener();
  }, []);

  return (
    <SafeAreaProvider>
      <AppNavigator />
    </SafeAreaProvider>
  );
}
