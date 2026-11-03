"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { clearToken, getToken } from "@/lib/api";

export default function NavBar() {
  const router = useRouter();

  function signOut() {
    clearToken();
    router.push("/login");
  }

  return (
    <header className="nav">
      <Link href="/" className="brand">
        MindBridge
      </Link>
      <nav className="nav-links">
        <Link href="/assignments">Assignments</Link>
        <Link href="/import">Import from Canvas</Link>
        {getToken() ? (
          <button type="button" className="link-button" onClick={signOut}>
            Sign out
          </button>
        ) : (
          <Link href="/login">Sign in</Link>
        )}
      </nav>
    </header>
  );
}
