import { LoadingState } from "@/components/shared/states";

export default function AppLoading() {
  return (
    <div className="p-6">
      <LoadingState label="Loading…" />
    </div>
  );
}
