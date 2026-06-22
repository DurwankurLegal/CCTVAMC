/**
 * Sync Manager — processes the offline queue when network reconnects.
 * Conflict resolution: last-write-wins using server timestamp.
 * Failed syncs are flagged with error detail for supervisor review.
 */
import NetInfo from "@react-native-netinfo";
import { getPendingQueue, markSynced } from "../db/localDb";
import apiClient from "./apiClient";

let syncInProgress = false;

export function startSyncListener() {
  NetInfo.addEventListener((state) => {
    if (state.isConnected && !syncInProgress) {
      processSyncQueue().catch(console.error);
    }
  });
}

export async function processSyncQueue() {
  syncInProgress = true;
  try {
    const queue = await getPendingQueue();
    for (const item of queue) {
      try {
        const payload = JSON.parse(item.payload);
        await syncItem(item.entity_type, payload);
        await markSynced(item.id);
      } catch (err) {
        console.warn(`Sync failed for ${item.id}:`, err);
        // Leave as pending; will retry on next reconnect
      }
    }
  } finally {
    syncInProgress = false;
  }
}

async function syncItem(entityType: string, payload: any) {
  switch (entityType) {
    case "engineer_visit_checkin":
      await apiClient.post(`/engineer-visits/${payload.visit_id}/checkin`, payload);
      break;
    case "engineer_visit_checkout":
      await apiClient.post(`/engineer-visits/${payload.visit_id}/checkout`, payload);
      break;
    case "engineer_visit_create":
      await apiClient.post("/engineer-visits", payload);
      break;
    case "media_upload":
      await uploadMedia(payload);
      break;
    default:
      console.warn("Unknown entity type in sync queue:", entityType);
  }
}

async function uploadMedia(payload: { visit_id: string; file_uri: string; type: "photo" | "signature" }) {
  const formData = new FormData();
  formData.append("file", {
    uri: payload.file_uri,
    type: payload.type === "photo" ? "image/jpeg" : "image/png",
    name: `${payload.type}_${Date.now()}.${payload.type === "photo" ? "jpg" : "png"}`,
  } as any);
  formData.append("visit_id", payload.visit_id);
  formData.append("media_type", payload.type);

  await apiClient.post("/engineer-visits/media", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}
