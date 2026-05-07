import { useEffect, useState } from "react";

import { currentTreeHeight } from "@/lib/file-tree";

export function useFileTreeHeight() {
  const [height, setHeight] = useState(() =>
    currentTreeHeight(typeof window === "undefined" ? null : window.innerHeight),
  );

  useEffect(() => {
    const updateHeight = () => setHeight(currentTreeHeight(window.innerHeight));
    window.addEventListener("resize", updateHeight);
    return () => window.removeEventListener("resize", updateHeight);
  }, []);

  return height;
}
