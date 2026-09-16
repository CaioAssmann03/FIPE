import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist-sans",
});

export const metadata: Metadata = {
  title: "FIPE AI",
  description:
    "Agente inteligente para consulta de preços de veículos na Tabela FIPE, usando Gemini Function Calling.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={geist.variable}>
      <body className="min-h-screen bg-slate-950 font-sans text-slate-100 antialiased">{children}</body>
    </html>
  );
}
