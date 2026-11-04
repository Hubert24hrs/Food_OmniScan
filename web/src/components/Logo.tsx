export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#0F766E" />
          <stop offset="1" stopColor="#134E4A" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill="url(#lg)" />
      <g fill="none" stroke="#5EEAD4" strokeWidth="4" strokeLinecap="round">
        <path d="M14 22v-6a2 2 0 0 1 2-2h6" />
        <path d="M42 14h6a2 2 0 0 1 2 2v6" />
        <path d="M50 42v6a2 2 0 0 1-2 2h-6" />
        <path d="M22 50h-6a2 2 0 0 1-2-2v-6" />
      </g>
      <circle cx="32" cy="32" r="11" fill="none" stroke="#fff" strokeWidth="4" />
      <path d="M27.5 36.5c0-6 4-9.5 9.5-9.5 0 6-3.5 9.5-9.5 9.5z" fill="#5EEAD4" />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="flex items-center gap-2">
      <LogoMark />
      <span className="font-display text-lg font-extrabold tracking-tight">
        Food <span className="text-brand">omniScan</span>
      </span>
    </span>
  );
}
