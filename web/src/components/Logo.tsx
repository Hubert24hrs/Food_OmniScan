/** Brand mark: a fresh-green tile with white scanner corners around a leaf, and a tomato-red dot.
 *  Inline SVG so it stays crisp; the scan line and dot animate gently (see globals.css). */
export function LogoMark({ size = 34, animated = true }: { size?: number; animated?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <defs>
        <clipPath id="om-clip"><rect x="14" y="14" width="36" height="36" rx="4" /></clipPath>
      </defs>
      <rect width="64" height="64" rx="16" fill="#16a34a" />
      <g fill="none" stroke="#ffffff" strokeWidth="4.5" strokeLinecap="round">
        <path d="M13 23v-6a4 4 0 0 1 4-4h6" />
        <path d="M41 13h6a4 4 0 0 1 4 4v6" />
        <path d="M51 41v6a4 4 0 0 1-4 4h-6" />
        <path d="M23 51h-6a4 4 0 0 1-4-4v-6" />
      </g>
      <path d="M32 46c-7-3-10-9-9-16 6 1 9 6 9 12 0-6 3-11 9-12 1 7-2 13-9 16z" fill="#ffffff" />
      <path d="M32 45V34" stroke="#16a34a" strokeWidth="1.8" strokeLinecap="round" />
      {animated && (
        <g clipPath="url(#om-clip)">
          <rect className="logo-beam" x="14" y="31" width="36" height="2" rx="1" fill="#fef08a" />
        </g>
      )}
      <circle className={animated ? "logo-dot" : undefined} cx="47" cy="17" r="5" fill="#ef4444" stroke="#ffffff" strokeWidth="2" />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="flex items-center gap-2">
      <LogoMark />
      <span className="font-display text-lg font-extrabold tracking-tight">
        Food <span className="text-brand">omni</span><span className="text-accent">Scan</span>
      </span>
    </span>
  );
}
