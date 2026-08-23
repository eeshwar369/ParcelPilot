import { notFound } from "next/navigation";
import { AdminConsole, type AdminView } from "../page";

const adminViews = new Set(["dashboard", "insights", "tickets", "agreements"]);

export default async function AdminSectionPage({ params }: { params: Promise<{ view: string }> }) {
  const { view } = await params;
  if (!adminViews.has(view)) {
    notFound();
  }
  return <AdminConsole initialView={view as AdminView} />;
}
