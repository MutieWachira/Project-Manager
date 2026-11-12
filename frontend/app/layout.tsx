import type { Metadata } from "next";
import "./globals.css";

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
      <body>{children}</body>
    </html>
  );
}