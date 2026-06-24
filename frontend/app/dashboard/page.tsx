import { redirect } from "next/navigation";

// Backwards-compatibility: the old Dashboard is now Mission Control.
export default function DashboardRedirect() {
  redirect("/mission-control");
}
