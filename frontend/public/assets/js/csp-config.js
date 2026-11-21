/**
 * Content Security Policy Configuration
 */

function applyCSP() {
  const meta = document.createElement('meta');
  meta.httpEquiv = 'Content-Security-Policy';

  const cspRules = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com/swiper@11 https://fonts.googleapis.com",
    "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com/swiper@11 https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https:",
    "connect-src 'self' http://localhost:8000 ws://localhost:*",
    "frame-src 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'"
  ];

  meta.content = cspRules.join('; ');
  document.head.appendChild(meta);
  console.log('🛡️ CSP applied');
}

document.addEventListener('DOMContentLoaded', applyCSP);
