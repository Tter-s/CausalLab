/** CausaLab 品牌标：因果三角图（节点 + 关系边），颜色跟随主题渐变。 */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} role="img" aria-label="CausaLab">
      <defs>
        <linearGradient id="brand-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6366f1" />
          <stop offset="1" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="14" fill="url(#brand-g)" />
      <g stroke="#ffffff" strokeWidth="3" strokeLinecap="round" opacity="0.88" fill="none">
        <path d="M20 43 L32 21 L44 43" />
        <path d="M20 43 L44 43" />
      </g>
      <circle cx="20" cy="43" r="5" fill="#ffffff" />
      <circle cx="44" cy="43" r="5" fill="#ffffff" />
      <circle cx="32" cy="21" r="5.5" fill="#ffffff" />
    </svg>
  );
}
