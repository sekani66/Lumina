// SVG icons 
const c  = (active) => active ? '#63c8ff' : 'rgba(226,244,255,0.3)'
const sw = 1.8

export const MailIcon = ({ active }) => ( 
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke={c(active)} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="4" width="20" height="16" rx="2"/>
        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
    </svg>
)

export const LockIcon = ({ active }) => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke={c(active)} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2"/>
        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
)

export const EyeIcon = () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke="rgba(226,244,255,0.3)" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/>
        <circle cx="12" cy="12" r="3"/>
    </svg>
)

export const EyeOffIcon = () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke="rgba(99,200,255,0.65)" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
        <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
)

export const CheckIcon = () => (
    <svg width="9" height="9" viewBox="0 0 24 24" fill="none"
        stroke="#07111f" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12"/>
    </svg>
)

export const ArrowLeft = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m15 18-6-6 6-6"/>
    </svg>
)

export const GoogleIcon = () => (
    <svg width="17" height="17" viewBox="0 0 24 24">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
)

export const MicrosoftIcon = () => (
    <svg width="17" height="17" viewBox="0 0 24 24">
        <rect x="1"  y="1"  width="10" height="10" fill="#f25022"/>
        <rect x="13" y="1"  width="10" height="10" fill="#7fba00"/>
        <rect x="1"  y="13" width="10" height="10" fill="#00a4ef"/>
        <rect x="13" y="13" width="10" height="10" fill="#ffb900"/>
    </svg>
)
