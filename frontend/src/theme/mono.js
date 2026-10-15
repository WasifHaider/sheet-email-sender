// Mono theme — light and dark variants. Monochrome UI chrome (black/white,
// pill-shaped controls) with colored status accents, ported from the
// approved Claude Design prototype ("Sheet Email Sender.dc.html").

export const LIGHT = {
  bg: '#f5f5f3',
  nav: 'rgba(245,245,243,.8)',
  card: '#ffffff',
  well: '#fafaf8',
  ink: '#0c0c0c',
  muted: '#76766f',
  line: '#e8e8e4',
  dash: '#cfcfc8',
  chipBg: '#ecece8',
  accent: '#0c0c0c',
  btn: '#0c0c0c',
  btnInk: '#ffffff',
  btnShadow: '0 1px 2px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.18)',
  shadow: '0 1px 1px rgba(0,0,0,.03),0 2px 4px rgba(0,0,0,.03),0 12px 28px -12px rgba(0,0,0,.1)',
  shadowSm: '0 1px 3px rgba(0,0,0,.1)',
  r: '24px',
  r2: '20px',
  r3: '999px',
  logoR: '50%',
  br: '999px',
  ok: ['#e8f6ec', '#1a7a3c'],
  sc: ['#fdf2dc', '#8f5d00'],
  fl: ['#fceceb', '#b3261e'],
  pn: ['#eeeeea', '#6a6a64']
}

export const DARK = {
  bg: '#101010',
  nav: 'rgba(16,16,16,.8)',
  card: '#1a1a1a',
  well: '#161616',
  ink: '#f5f5f3',
  muted: '#8f8f88',
  line: '#2a2a27',
  dash: '#3a3a36',
  chipBg: '#222220',
  accent: '#f5f5f3',
  btn: '#f5f5f3',
  btnInk: '#0c0c0c',
  btnShadow: '0 1px 2px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.08)',
  shadow: '0 1px 1px rgba(0,0,0,.2),0 2px 4px rgba(0,0,0,.3),0 12px 28px -12px rgba(0,0,0,.6)',
  shadowSm: '0 1px 3px rgba(0,0,0,.5)',
  r: '24px',
  r2: '20px',
  r3: '999px',
  logoR: '50%',
  br: '999px',
  ok: ['rgba(34,197,94,.16)', '#4ade80'],
  sc: ['rgba(245,158,11,.16)', '#fbbf24'],
  fl: ['rgba(239,68,68,.16)', '#f87171'],
  pn: ['rgba(148,148,140,.18)', '#b0b0a8']
}

export const ICON = {
  sent: ['M5 12.5l4.5 4.5L19 7', ''],
  scheduled: ['M12 7v5l3 2', 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z'],
  failed: ['M12 8v5M12 16.5v.5', 'M10.3 4l-8 14a2 2 0 0 0 1.7 3h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0z'],
  pending: ['M7 3h7l5 5v13H7z', 'M14 3v5h5']
}

export function chipStyle(key, t) {
  const c = { sent: t.ok, scheduled: t.sc, failed: t.fl, pending: t.pn }[key] || t.pn
  return `display:inline-flex;align-items:center;gap:6px;padding:4px 10px 4px 8px;border-radius:999px;font-size:12px;font-weight:600;background:${c[0]};color:${c[1]}`
}

export function statIconStyle(key, t) {
  const c = { sent: t.ok, scheduled: t.sc, failed: t.fl, pending: t.pn }[key] || t.pn
  return `width:40px;height:40px;border-radius:12px;display:grid;place-items:center;background:${c[0]};color:${c[1]}`
}

export function btnBase() {
  return "display:inline-flex;align-items:center;justify-content:center;gap:8px;font:600 14px 'Geist',sans-serif;padding:12px 20px;cursor:pointer;"
}

export function primaryStyle(t) {
  return `${btnBase()}border:0;border-radius:${t.br};color:${t.btnInk};background:${t.btn};box-shadow:${t.btnShadow}`
}

export function secondaryStyle(t) {
  return `${btnBase()}border-radius:${t.br};color:${t.ink};background:${t.card};border:1px solid ${t.line};box-shadow:${t.shadowSm}`
}

export function navLinkStyle(active, t) {
  return `font-size:14px;font-weight:600;text-decoration:none;padding:7px 14px;border-radius:999px;color:${active ? t.ink : t.muted};background:${active ? t.chipBg : 'transparent'}`
}

export function stepStyle(active, t) {
  return `font-weight:${active ? 600 : 500};color:${active ? t.ink : t.muted}`
}
