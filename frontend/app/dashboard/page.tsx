import { redirect } from "next/navigation";

type Props = {
  searchParams: {
    symbol?: string;
  };
};

export default function DashboardRedirectPage({ searchParams }: Props) {
  const symbol = (searchParams.symbol ?? "AAPL").toUpperCase();
  redirect(`/terminal?symbol=${encodeURIComponent(symbol)}`);
}
