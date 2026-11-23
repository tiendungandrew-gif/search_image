import type { SVGProps } from "react";

export function Icon({
  kind,
  ...props
}: SVGProps<SVGSVGElement> & {
  kind:
    | "search"
    | "image"
    | "camera"
    | "mic"
    | "arrow"
    | "layers"
    | "refresh"
    | "sun"
    | "moon"
    | "sliders"
    | "hotel"
    | "palm"
    | "pool"
    | "compass";
}) {
  const paths = {
    hotel: (
      <>
        <path d="M4 21V4a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v17M2 21h20M9 21v-5h6v5M8 7h1m6 0h1M8 11h1m6 0h1" />
      </>
    ),
    palm: (
      <>
        <path d="M11 21c3-4 3-9 2-13M13 8C9 3 5 4 3 8c4-2 7-1 10 0Zm0 0c2-5 7-5 9-1-4-1-6 0-9 1Zm0 0c-4 0-6 3-6 6 3-3 4-4 6-6Zm0 0c4 0 6 2 6 5-2-2-4-4-6-5ZM4 21h16" />
      </>
    ),
    pool: (
      <>
        <path d="M2 18c2-2 4 2 6 0s4 2 6 0 4 2 6 0M2 22c2-2 4 2 6 0s4 2 6 0 4 2 6 0M7 15V5a2 2 0 0 1 4 0m3 10V5a2 2 0 0 1 4 0M7 8h7M7 12h7" />
      </>
    ),
    compass: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m16 8-2.5 5.5L8 16l2.5-5.5L16 8Z" />
      </>
    ),
    sliders: (
      <>
        <path d="M4 7h8m4 0h4M4 17h3m4 0h9" />
        <circle cx="14" cy="7" r="2" />
        <circle cx="9" cy="17" r="2" />
      </>
    ),
    sun: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" />
      </>
    ),
    moon: <path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z" />,
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 4 4" />
      </>
    ),
    camera: (
      <>
        <path d="M8 5 9.5 3h5L16 5h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4Z" />
        <circle cx="12" cy="13" r="4" />
      </>
    ),
    mic: (
      <>
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path d="M5 10a7 7 0 0 0 14 0M12 17v4m-4 0h8" />
      </>
    ),
    image: (
      <>
        <rect x="3" y="3" width="18" height="18" rx="4" />
        <circle cx="8" cy="8" r="1.5" />
        <path d="m3 17 5-5 4 4 3-6 6 8" />
      </>
    ),
    arrow: (
      <>
        <path d="M5 12h14m-6-6 6 6-6 6" />
      </>
    ),
    layers: (
      <>
        <path d="m12 3 10 6-10 6L2 9l10-6Zm-9 11 9 5 9-5M3 18l9 5 9-5" />
      </>
    ),
    refresh: (
      <>
        <path d="M20 7v5h-5M4 17v-5h5" />
        <path d="M5.5 8a7 7 0 0 1 12-3L20 8M4 16l2.5 3A7 7 0 0 0 18.5 16" />
      </>
    ),
  };
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {paths[kind]}
    </svg>
  );
}
