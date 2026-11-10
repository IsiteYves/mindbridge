import { useEffect } from "react";
import { useNavigate } from "react-router";

import { getToken } from "@/lib/api";

export function useRequireAuth(): void {
  const navigate = useNavigate();

  useEffect(() => {
    if (!getToken()) navigate("/login", { replace: true });
  }, [navigate]);
}
