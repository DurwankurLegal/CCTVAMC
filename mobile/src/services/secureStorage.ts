/**
 * Secure token storage backed by the iOS Keychain / Android Keystore via
 * react-native-keychain (TAD security requirement). Tokens must NEVER be kept in
 * AsyncStorage, which is unencrypted plaintext.
 *
 * Access and refresh tokens are stored under separate Keychain "services" so the
 * short-lived access token can be rotated without touching the refresh token.
 */
import * as Keychain from "react-native-keychain";

const ACCESS_SERVICE = "cctv.access_token";
const REFRESH_SERVICE = "cctv.refresh_token";
// A fixed username is required by the Keychain API; the secret is the token.
const ACCOUNT = "cctv";

export async function setTokens(accessToken: string, refreshToken: string): Promise<void> {
  await Keychain.setGenericPassword(ACCOUNT, accessToken, {
    service: ACCESS_SERVICE,
    accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
  await Keychain.setGenericPassword(ACCOUNT, refreshToken, {
    service: REFRESH_SERVICE,
    accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function setAccessToken(accessToken: string): Promise<void> {
  await Keychain.setGenericPassword(ACCOUNT, accessToken, {
    service: ACCESS_SERVICE,
    accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function getAccessToken(): Promise<string | null> {
  const creds = await Keychain.getGenericPassword({ service: ACCESS_SERVICE });
  return creds ? creds.password : null;
}

export async function getRefreshToken(): Promise<string | null> {
  const creds = await Keychain.getGenericPassword({ service: REFRESH_SERVICE });
  return creds ? creds.password : null;
}

/** Clear all tokens on logout / refresh failure. */
export async function clearTokens(): Promise<void> {
  await Keychain.resetGenericPassword({ service: ACCESS_SERVICE });
  await Keychain.resetGenericPassword({ service: REFRESH_SERVICE });
}
