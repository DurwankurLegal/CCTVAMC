import Geolocation from "react-native-geolocation-service";
import { Platform, PermissionsAndroid } from "react-native";

export async function requestLocationPermission(): Promise<boolean> {
  if (Platform.OS === "android") {
    const granted = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
      {
        title: "Location Permission",
        message: "CCTV Technician app needs location access for GPS check-in/check-out.",
        buttonPositive: "Allow",
      }
    );
    return granted === PermissionsAndroid.RESULTS.GRANTED;
  }
  const auth = await Geolocation.requestAuthorization("whenInUse");
  return auth === "granted";
}

export interface GeoCoords {
  lat: number;
  lng: number;
  accuracy: number;
}

export function getCurrentLocation(): Promise<GeoCoords> {
  return new Promise((resolve, reject) => {
    Geolocation.getCurrentPosition(
      (pos) =>
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        }),
      (err) => reject(err),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 }
    );
  });
}
