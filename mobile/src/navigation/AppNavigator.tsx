import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createStackNavigator } from "@react-navigation/stack";
import LoginScreen from "../screens/LoginScreen";
import TicketListScreen from "../screens/TicketListScreen";
import VisitDetailScreen from "../screens/VisitDetailScreen";

const Stack = createStackNavigator();

export default function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Login">
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
        <Stack.Screen
          name="Main"
          component={TicketListScreen}
          options={{ title: "My Tickets", headerStyle: { backgroundColor: "#1e3a5f" }, headerTintColor: "#fff" }}
        />
        <Stack.Screen
          name="VisitDetail"
          component={VisitDetailScreen}
          options={{ title: "Service Visit", headerStyle: { backgroundColor: "#1e3a5f" }, headerTintColor: "#fff" }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
