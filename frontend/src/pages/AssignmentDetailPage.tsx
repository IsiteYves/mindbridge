import { useParams } from "react-router";

import AssignmentView from "@/pages/AssignmentView";

export default function AssignmentDetailPage() {
  const { id = "" } = useParams();
  return <AssignmentView id={id} />;
}
