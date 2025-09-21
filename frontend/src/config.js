import { Capacitor } from '@capacitor/core';

let API_BASE_URL;

if (Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android') {
  API_BASE_URL = "http://10.0.2.2:8000"; // Android emulator bridge
} else {
  API_BASE_URL = "http://127.0.0.1:8000"; // Browser dev
}

export { API_BASE_URL };
