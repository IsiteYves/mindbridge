import { type RefObject, useEffect } from "react";

export function useCloseOnOutsideClick(ref: RefObject<HTMLDetailsElement | null>): void {
  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      const element = ref.current;
      if (element?.open && !element.contains(event.target as Node)) element.removeAttribute("open");
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [ref]);
}
