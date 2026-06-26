import React from "react";
import { View, TouchableOpacity, Text } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createStackNavigator } from "@react-navigation/stack";
import LoginScreen from "../screens/LoginScreen";
import TicketListScreen from "../screens/TicketListScreen";
import VisitDetailScreen from "../screens/VisitDetailScreen";
import SyncStatusScreen from "../screens/SyncStatusScreen";
import RecordCashScreen from "../screens/RecordCashScreen";

const Stack = createStackNavigator();

export default function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Login">
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
        <Stack.Screen
          name="Main"
          component={TicketListScreen}
          options={({ navigation }: any) => ({
            title: "My Tickets",
            headerStyle: { backgroundColor: "#1e3a5f" },
            headerTintColor: "#fff",
            headerRight: () => (
              <View style={{ flexDirection: "row", marginRight: 15 }}>
                <TouchableOpacity
                  style={{ marginRight: 15 }}
                  onPress={() => navigation.navigate("RecordCash")}
                >
                  <Text style={{ color: "#fff", fontWeight: "600", fontSize: 14 }}>💵 Cash</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => navigation.navigate("SyncStatus")}
                >
                  <Text style={{ color: "#fff", fontWeight: "600", fontSize: 14 }}>🔄 Sync</Text>
                </TouchableOpacity>
              </View>
            ),
          })}
        />
        <Stack.Screen
          name="VisitDetail"
          component={VisitDetailScreen}
          options={{ title: "Service Visit", headerStyle: { backgroundColor: "#1e3a5f" }, headerTintColor: "#fff" }}
        />
        <Stack.Screen
          name="RecordCash"
          component={RecordCashScreen}
          options={{ title: "Record Cash", headerStyle: { backgroundColor: "#1e3a5f" }, headerTintColor: "#fff" }}
        />
        <Stack.Screen
          name="SyncStatus"
          component={SyncStatusScreen}
          options={{ title: "Sync Status", headerStyle: { backgroundColor: "#1e3a5f" }, headerTintColor: "#fff" }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
