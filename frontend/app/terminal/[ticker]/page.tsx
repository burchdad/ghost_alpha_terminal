import { redirect } from "next/navigation";

type Props = {
  params: { ticker: string };
};

export default function TerminalTickerPage({ params }: Props) {
  const ticker = (params.ticker ?? "AAPL").toUpperCase();
  redirect(`/dashboard?symbol=${encodeURIComponent(ticker)}`);
}
