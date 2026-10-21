import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { DEFAULT_BIO } from '../utils/profile.js';

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
          {/* 로그인 중: 로그아웃 옆에 프로필 사진, 이름, 소개 글 */}
          {loggedIn && me && (
            <div className="topnav-profile">
              <span className="topnav-avatar">{me.avatar_url && <img src={me.avatar_url} alt="" />}</span>
              <span className="topnav-profile-text">
                <strong>{me.name}</strong>
                <span>{me.bio || DEFAULT_BIO}</span>
              </span>
            </div>
          )}
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
