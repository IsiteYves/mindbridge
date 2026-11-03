"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getToken } from "@/lib/api";

export function useRequireAuth(): void {
  const router = useRouter();

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);
}
