import { Suspense } from "react";

import AssignmentView from "./AssignmentView";

async function Detail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AssignmentView id={id} />;
}

export default function AssignmentPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<p className="muted">Loading…</p>}>
      <Detail params={params} />
    </Suspense>
  );
}
