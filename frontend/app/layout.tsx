import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Giva Template Studio",
  description: "Create WhatsApp and push notification templates for Giva.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
