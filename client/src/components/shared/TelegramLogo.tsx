interface TelegramLogoProps {
  size?: number;
  mono?: boolean;
}

export function TelegramLogo({ size = 40, mono = false }: TelegramLogoProps) {
  const fill = mono ? 'currentColor' : '#229ED9';
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      {!mono && <circle cx="20" cy="20" r="20" fill="#229ED9" />}
      <path
        d="M10.5 19.2 L28.4 12.4 C29.3 12.1 30 12.6 29.7 13.6 L26.8 27.6 C26.6 28.6 25.9 28.8 25.2 28.4 L21 25.4 L19 27.3 C18.7 27.6 18.5 27.8 18 27.8 L18.3 23.7 L26 16.8 C26.3 16.5 25.9 16.4 25.5 16.6 L16 22.5 L11.9 21.2 C11 20.9 11 20.3 12 19.9 Z"
        fill={mono ? fill : '#fff'}
      />
    </svg>
  );
}
