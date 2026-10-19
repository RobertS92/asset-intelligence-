import AuctionFinder from "@/components/AuctionFinder";
import type { ListingsPayload } from "@/lib/listings";
import styles from "./page.module.css";

async function loadListings(): Promise<ListingsPayload> {
  const base = process.env.NEXT_PUBLIC_LISTINGS_URL ?? "/data/listings.json";
  // Prefer filesystem read at build/runtime so Vercel does not need a self-HTTP loop.
  if (base.startsWith("/")) {
    const { readFile } = await import("node:fs/promises");
    const { join } = await import("node:path");
    const path = join(process.cwd(), "public", base.replace(/^\//, ""));
    const raw = await readFile(path, "utf8");
    return JSON.parse(raw) as ListingsPayload;
  }
  const res = await fetch(base, { next: { revalidate: 300 } });
  if (!res.ok) {
    throw new Error(`Failed to load listings from ${base}: ${res.status}`);
  }
  return (await res.json()) as ListingsPayload;
}

export default async function HomePage() {
  const payload = await loadListings();

  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.brand}>Exodus Asset Signals</p>
        <h1 className={styles.title}>Auction Finder</h1>
        <p className={styles.lede}>
          One normalized feed of tax sales, trustee sales, and Ch.&nbsp;683 vehicle auctions
          across the Texas core counties. Demographic data never enters this view.
        </p>
      </header>
      <AuctionFinder listings={payload.listings} generatedFrom={payload.generated_from} />
    </main>
  );
}
