import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Bind IPv4 loopback explicitly — plain "localhost" can resolve to an
  // unreachable ::1 binding on some Windows setups.
  server: { host: "127.0.0.1" },
  preview: { host: "127.0.0.1" },
});
