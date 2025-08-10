import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Synapse - AI Assistant",
  description: "Your intelligent AI assistant with RAG capabilities",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-50">
        {children}
      </body>
    </html>
  );
}
