import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "../components/providers/auth-provider";

export const metadata: Metadata = {
  title: {
    default: "SherlskyyCommand",
    template: "%s | SherlskyyCommand",
  },
  description:
    "A centralized project management and administration platform for software applications.",
  applicationName: "SherlskyyCommand",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}