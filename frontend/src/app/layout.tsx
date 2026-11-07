import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: { default: "BPDB Intelligence", template: "%s | BPDB Intelligence" },
  description: "BPDB national data, trend analysis, forecasting results and research evidence.",
  robots: { index: false, follow: false },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
