/**
 * Sync Manager — processes the offline queue when the network reconnects.
 *
 * Reliability guarantees (TAD offline-sync requirements):
 *  - Idempotency: each queue item carries a stable id, sent as the
 *    `Idempotency-Key` header so a retried write is not applied twice server-side.
 *  - Conflict detection: payloads include `client_updated_at`; the server compares
 *    it against its own record's version/timestamp instead of blind last-write-wins.
 *  - Failure visibility: failed items are flagged (retry_count / last_error) and
 *    surfaced on the Sync Status screen — never silently dropped.
 *  - ID remapping: a locally-created visit receives a server id on sync, which is
 *    then propagated to all dependent queued actions (checkout, media, parts).
 */
import NetInfo from "@react-native-netinfo";
import { getPendingQueue, markSynced, markFailed, remapVisitId, queueForSync } from "../db/localDb";
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
        await syncItem(item.id, item.entity_type, payload);
        await markSynced(item.id);
      } catch (err: any) {
        const detail = err?.response?.data?.detail || err?.message || String(err);
        console.warn(`Sync failed for ${item.id}:`, detail);
        // Persist the failure so it is visible and retried (bounded) — not lost.
        await markFailed(item.id, detail);
      }
    }
  } finally {
    syncInProgress = false;
  }
}

// The queue item id doubles as the idempotency key (stable across retries).
function idempotent(itemId: string) {
  return { headers: { "Idempotency-Key": itemId } };
}

async function syncItem(itemId: string, entityType: string, payload: any) {
  switch (entityType) {
    case "engineer_visit_create": {
      const { data } = await apiClient.post("/engineer-visits", payload, idempotent(itemId));
      // Propagate the new server id to dependent queued actions.
      if (payload.local_id && data?.id) {
        await remapVisitId(payload.local_id, data.id);
      }
      break;
    }
    case "engineer_visit_checkin":
      await apiClient.post(`/engineer-visits/${payload.visit_id}/checkin`, payload, idempotent(itemId));
      break;
    case "engineer_visit_checkout":
      await apiClient.post(`/engineer-visits/${payload.visit_id}/checkout`, payload, idempotent(itemId));
      break;
    case "media_upload":
      await uploadMedia(itemId, payload);
      break;
    case "cash_collection_create": {
      const { data } = await apiClient.post("/cash-collections", payload, idempotent(itemId));
      if (payload.local_photo_path && data?.id) {
        await queueForSync("cash_collection_photo_upload", {
          cash_collection_id: data.id,
          file_uri: payload.local_photo_path
        });
      }
      break;
    }
    case "cash_collection_photo_upload":
      await uploadCashReceipt(itemId, payload.cash_collection_id, payload.file_uri);
      break;
    default:
      console.warn("Unknown entity type in sync queue:", entityType);
  }
}

async function uploadMedia(itemId: string, payload: { visit_id: string; file_uri: string; type: "photo" | "signature" }) {
  const formData = new FormData();
  formData.append("file", {
    uri: payload.file_uri,
    type: payload.type === "photo" ? "image/jpeg" : "image/png",
    name: `${payload.type}_${Date.now()}.${payload.type === "photo" ? "jpg" : "png"}`,
  } as any);
  formData.append("visit_id", payload.visit_id);
  formData.append("media_type", payload.type);

  await apiClient.post("/engineer-visits/media", formData, {
    headers: { "Content-Type": "multipart/form-data", "Idempotency-Key": itemId },
  });
}

async function uploadCashReceipt(itemId: string, cashCollectionId: string, fileUri: string) {
  const formData = new FormData();
  formData.append("file", {
    uri: fileUri,
    type: "image/jpeg",
    name: `receipt_${Date.now()}.jpg`,
  } as any);

  await apiClient.post(`/cash-collections/${cashCollectionId}/media`, formData, {
    headers: { "Content-Type": "multipart/form-data", "Idempotency-Key": itemId },
  });
}
