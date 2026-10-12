/* 로그인 상태와 로그인 팝업.
   지금은 시연용으로 아이디 test / 비밀번호 test 로만 로그인되고, 로그인 상태는 이 브라우저에만 저장한다.
   서버 연동 때 login() 안을 서버 로그인 요청으로 바꾼다. */
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import useToast from '../components/useToast.js';

const KEY = 'moa_logged_in';
const DEMO_ID = 'test';
const DEMO_PW = 'test';
const WELCOME = 'MOA에 오신 것을 환영합니다.';
const NEED_LOGIN = '합성하려면 로그인이 필요합니다.';

const read = () => { try { return localStorage.getItem(KEY) === '1'; } catch { return false; } };
const write = (on) => {
  try { if (on) localStorage.setItem(KEY, '1'); else localStorage.removeItem(KEY); } catch { /* 저장 불가 시 무시 */ }
};

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [loggedIn, setLoggedIn] = useState(read);
  const [modal, setModal] = useState({ open: false, sub: WELCOME, next: null });
  const [toast, showToast] = useToast(2000);
  const navigate = useNavigate();
  const location = useLocation();

  const openLogin = useCallback((next = null) => {
    setModal({ open: true, sub: next ? NEED_LOGIN : WELCOME, next });
  }, []);

  const closeLogin = useCallback(() => setModal({ open: false, sub: WELCOME, next: null }), []);

  // 합성하기 화면에서 튕겨 왔을 때 로그인 팝업을 바로 연다
  useEffect(() => {
    if (location.state && location.state.needLogin && !loggedIn) {
      openLogin('/studio');
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location, loggedIn, openLogin, navigate]);

  const login = (id, pw) => {
    if (id === DEMO_ID && pw === DEMO_PW) {
      write(true);
      setLoggedIn(true);
      const next = modal.next;
      closeLogin();
      if (next) navigate(next);
      else showToast('로그인되었습니다');
      return true;
    }
    showToast('아이디 또는 비밀번호가 올바르지 않습니다');
    return false;
  };

  const logout = () => {
    write(false);
    setLoggedIn(false);
    if (location.pathname === '/studio') navigate('/', { replace: true });
    showToast('로그아웃되었습니다');
  };

  const value = { loggedIn, openLogin, login, logout, showToast };

  return (
    <AuthContext.Provider value={value}>
      {children}
      <LoginModal modal={modal} onClose={closeLogin} onSubmit={login} onSignup={() => showToast('회원가입은 준비 중입니다')} />
      <div className={'auth-toast' + (toast.show ? ' show' : '')}>{toast.msg}</div>
    </AuthContext.Provider>
  );
}

function LoginModal({ modal, onClose, onSubmit, onSignup }) {
  const [id, setId] = useState('');
  const [pw, setPw] = useState('');
  const firstInput = useRef(null);

  useEffect(() => {
    if (!modal.open) return undefined;
    const t = setTimeout(() => firstInput.current && firstInput.current.focus(), 0);
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => { clearTimeout(t); document.removeEventListener('keydown', onKey); };
  }, [modal.open, onClose]);

  const submit = (e) => {
    e.preventDefault();
    if (onSubmit(id.trim(), pw)) setPw('');
  };

  return (
    <div className={'auth-modal' + (modal.open ? ' open' : '')} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="auth-modal-box" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
        <button type="button" className="auth-modal-close" aria-label="닫기" onClick={onClose}>×</button>
        <h2 className="auth-modal-title" id="auth-modal-title">로그인</h2>
        <p className="auth-modal-sub">{modal.sub}</p>
        <form onSubmit={submit} noValidate>
          <label className="auth-field"><span>아이디</span><input ref={firstInput} type="text" placeholder="아이디를 입력하세요" autoComplete="username" value={id} onChange={(e) => setId(e.target.value)} /></label>
          <label className="auth-field"><span>비밀번호</span><input type="password" placeholder="비밀번호를 입력하세요" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} /></label>
          <button type="submit" className="auth-submit">로그인</button>
        </form>
        <p className="auth-modal-foot">아직 계정이 없으신가요? <a onClick={onSignup}>회원가입</a></p>
      </div>
    </div>
  );
}
