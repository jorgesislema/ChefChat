import { useState } from "react";

/** Logo: usa /logo.png si existe; si no, un mirlo en SVG. */
export function Logo({ size = 36 }: { size?: number }) {
  const [falla, setFalla] = useState(false);
  if (!falla)
    return <img src="/logo.png" width={size} height={size} alt="" className="rounded-lg object-contain" onError={() => setFalla(true)} />;
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <rect width="64" height="64" rx="14" fill="#17171A" />
      <path d="M14 38c0-10 8-18 18-18 5 0 8 2 10 4l12 2-10 5c0 10-8 18-18 18-7 0-12-5-12-11z" fill="#0E0E10" stroke="#3a3a42" strokeWidth="1.5" />
      <path d="M44 26l12 3-12 4z" fill="#F5A31A" />
      <circle cx="40" cy="27" r="1.8" fill="#F4F1EA" />
    </svg>
  );
}
