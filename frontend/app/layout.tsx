import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "ALGONOX RAG MODEL | Grounded Document Intelligence",
  description: "Enterprise-grade Multimodal Retrieval-Augmented Generation (RAG) platform with multi-portal document scraping & semantic reranking.",
  viewport: "width=device-width, initial-scale=1",
  icons: {
    icon: "/favicon.ico"
  }
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <head>
        {/* Import premium Orbitron and Inter fonts directly from Google CDN */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Orbitron:wght@400;500;700;900&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-cyber-bg text-slate-100 min-h-screen antialiased select-none font-sans overflow-x-hidden">
        {children}
      </body>
    </html>
  )
}
