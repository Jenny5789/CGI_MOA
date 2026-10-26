import { useEffect, useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';

// 합성하기 화면으로 가는 링크. 로그인하지 않았으면 이동을 막고 로그인 팝업을 띄운다.
export function StudioLink({ className, children }) {
  const { loggedIn, openLogin } = useAuth();
  const onClick = (e) => {
    if (loggedIn) return;
    e.preventDefault();
    openLogin('/studio');
  };
  return <Link className={className} to="/studio" onClick={onClick}>{children}</Link>;
}

const navClass = ({ isActive }) => 'nav-item' + (isActive ? ' active' : '');

export default function TopNav() {
  const { loggedIn, me, openLogin, openSignup, logout } = useAuth();

  return (
    <header className="topnav">
      <div className="topnav-row1">
        <div className="topnav-left">
          <Link className="brand" to="/">
            <span className="brand-name">MOA</span>
          </Link>
          <nav className="nav">
            <NavLink className={navClass} to="/" end>홈</NavLink>
            <GatedNavLink to="/studio">합성하기</GatedNavLink>
            <GatedNavLink to="/mypage">마이페이지</GatedNavLink>
          </nav>
        </div>
        <div className="topnav-auth">
          {!loggedIn && (
            <a className="auth-btn" href="#" onClick={(e) => { e.preventDefault(); openSignup(); }}>회원가입</a>
          )}
          {/* 로그인 중: 프로필 사진과 닉네임 환영 문구, 로그인 남은 시간, 로그아웃 순서 */}
          {loggedIn && me && (
            <div className="topnav-profile">
              <span className="topnav-avatar">{me.avatar_url && <img src={me.avatar_url} alt="" />}</span>
              <span className="topnav-profile-text">
                <strong>{me.name} 님</strong>
                <span>어서오세요</span>
              </span>
            </div>
          )}
          {loggedIn && <LoginTimer />}
          <a
            className="auth-btn auth-btn-primary"
            href="#"
            onClick={(e) => { e.preventDefault(); if (loggedIn) logout(); else openLogin(); }}
          >
            {loggedIn ? '로그아웃' : '로그인'}
          </a>
        </div>
      </div>
    </header>
  );
}

// 남은 시간 글자: 1시간 이상이면 2:59:41, 미만이면 29:59
const pad = (n) => String(n).padStart(2, '0');
function formatLeft(ms) {
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}:${pad(m)}:${pad(s % 60)}` : `${m}:${pad(s % 60)}`;
}

// 로그인 남은 시간과 연장 버튼. 1초마다 이 부분만 다시 그린다 (만료 처리와 안내 창은 auth/ExpiryNotice.jsx)
function LoginTimer() {
  const { expiresAt, extendLogin } = useAuth();
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!expiresAt) return undefined;
    setNow(Date.now());
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [expiresAt]);

  if (!expiresAt) return null;
  return (
    <div className="topnav-timer">
      <span className="topnav-timer-label">남은 시간</span>
      <span className="topnav-timer-time">{formatLeft(Math.max(0, expiresAt.getTime() - now))}</span>
      <button type="button" className="topnav-timer-btn" onClick={extendLogin}>연장</button>
    </div>
  );
}

// 메뉴의 '합성하기', '마이페이지': 현재 화면이면 active 표시, 로그인 전이면 이동을 막고 로그인 팝업
function GatedNavLink({ to, children }) {
  const { loggedIn, openLogin } = useAuth();
  return (
    <NavLink
      className={navClass}
      to={to}
      onClick={(e) => { if (!loggedIn) { e.preventDefault(); openLogin(to); } }}
    >
      {children}
    </NavLink>
  );
}
