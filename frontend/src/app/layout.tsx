import type { Metadata, Viewport } from "next";
import { Fraunces, IBM_Plex_Mono, Inter } from "next/font/google";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-display",
  display: "swap",
});

const sans = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://papers.scottcampbell.io"),
  title: "arXiv paper recommender: four recommenders and a popularity baseline",
  description:
    "Pick any arXiv computer science paper from 2019 on and compare four recommenders (TF-IDF, a sentence transformer, citation graph ALS and a tuned hybrid) and a popularity baseline, with held out evaluation and live latency.",
  applicationName: "arXiv Recommender",
  authors: [{ name: "Scott Campbell", url: "https://scottcampbell.io/" }],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "arXiv Recommender",
    title: "arXiv paper recommender: four recommenders and a popularity baseline",
    description: "A hybrid paper recommender on the OpenAlex CS corpus. Compare four recommenders and a popularity baseline head to head, with held out evaluation and sub 100 ms serving.",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "arXiv Recommender comparing four recommenders and a popularity baseline" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "arXiv paper recommender: four recommenders and a popularity baseline",
    description: "A hybrid paper recommender on the OpenAlex CS corpus. Compare four recommenders and a popularity baseline head to head, with held out evaluation and sub 100 ms serving.",
    images: ["/og-image.png"],
  },
};

// Structured data for search engines.
const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "arXiv Recommender",
  "url": "https://papers.scottcampbell.io/",
  "description": "Pick any arXiv computer science paper from 2019 on and compare four recommenders (TF-IDF, a sentence transformer, citation graph ALS and a tuned hybrid) and a popularity baseline, with held out evaluation and live latency.",
  "applicationCategory": "ReferenceApplication",
  "operatingSystem": "Any (web browser)",
  "isAccessibleForFree": true,
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  },
  "author": {
    "@type": "Person",
    "name": "Scott Campbell",
    "url": "https://scottcampbell.io/"
  },
  "subjectOf": {
    "@type": "CreativeWork",
    "name": "arXiv Recommender case study",
    "url": "https://scottcampbell.io/projects/arxiv-recommender/"
  },
  "sameAs": [
    "https://github.com/scottcampbelldata/arxiv-recommender"
  ]
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FAFAFC" },
    { media: "(prefers-color-scheme: dark)", color: "#101015" },
  ],
};

// Resolve the theme before first paint so there is no flash of the wrong mode.
const themeScript = `(function(){try{var t=localStorage.getItem('theme');var sys=window.matchMedia('(prefers-color-scheme: dark)').matches;var dark=t==='dark'||((!t||t==='system')&&sys);var el=document.documentElement;el.classList.toggle('dark',dark);el.style.colorScheme=dark?'dark':'light';}catch(e){}})();`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${display.variable} ${sans.variable} ${mono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
