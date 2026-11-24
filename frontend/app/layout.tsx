import "./globals.css";

export const metadata = { title: "TrialTrace", description: "Traceable clinical trial extraction" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
