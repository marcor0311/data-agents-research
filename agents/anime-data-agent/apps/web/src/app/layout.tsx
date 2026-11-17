import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Anime Data Agent — Explorá cada historia",
  description: "Explorá el catálogo de anime, compará entregas y descubrí patrones con datos verificables.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body>{children}</body></html>;
}
