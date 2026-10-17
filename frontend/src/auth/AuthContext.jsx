/* 로그인 상태와 로그인 팝업, 회원가입 팝업(SignupModal.jsx).
   로그인 요청은 src/api/auth.js가 보낸다. 서버가 없는 지금은 가짜 서버가 아이디 test / 비밀번호 test 로만 로그인시킨다.
   로그인하면 받은 토큰을 이 브라우저에 저장하고, 토큰이 있으면 로그인된 상태로 본다. */
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import useToast from '../components/useToast.js';
import * as authApi from '../api/auth.js';
import SignupModal from './SignupModal.jsx';
import { getToken, UNAUTHORIZED_EVENT } from '../api/client.js';

const WELCOME = 'MOA에 오신 것을 환영합니다.';
const EXPIRED = '로그인이 만료되었습니다. 다시 로그인해 주세요.';
// 로그인해야 들어갈 수 있는 화면과, 막혔을 때 팝업에 보여 줄 문구
export const GATED = {
  '/studio': '합성하기는 로그인 후 이용할 수 있습니다.',
  '/mypage': '마이페이지는 로그인 후 이용할 수 있습니다.',
};

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [loggedIn, setLoggedIn] = useState(() => !!getToken());
  const [modal, setModal] = useState({ open: false, sub: WELCOME, next: null });
  const [signup, setSignup] = useState({ open: false, next: null }); // next: 가입 뒤 갈 화면 (로그인 창에서 넘어온 경우)
  const [toast, showToast] = useToast(2000);
  const navigate = useNavigate();
  const location = useLocation();

  const openLogin = useCallback((next = null) => {
    setModal({ open: true, sub: (next && GATED[next]) || WELCOME, next });
  }, []);

  const closeLogin = useCallback(() => setModal({ open: false, sub: WELCOME, next: null }), []);

  // 회원가입 창: 로그인 창이 열려 있었으면 닫고 연다
  const openSignup = useCallback((next = null) => {
    setModal({ open: false, sub: WELCOME, next: null });
    setSignup({ open: true, next });
  }, []);

  const closeSignup = useCallback(() => setSignup({ open: false, next: null }), []);

  // 로그인이 필요한 화면(합성하기, 마이페이지)에서 튕겨 왔을 때 로그인 팝업을 바로 연다
  useEffect(() => {
    if (location.state && location.state.needLogin && !loggedIn) {
      openLogin(location.state.next || '/studio');
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location, loggedIn, openLogin, navigate]);

  // 다른 요청을 하다가 로그인이 풀린 것을 알게 되면(client.js) 로그아웃 상태로 바꾸고 로그인 팝업을 연다
  useEffect(() => {
    const onExpired = () => {
      setLoggedIn(false);
      setModal({ open: true, sub: EXPIRED, next: location.pathname });
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onExpired);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onExpired);
  }, [location.pathname]);

  const login = async (username, pw) => {
    const next = modal.next;
    try {
      await authApi.login(username, pw);
    } catch (e) {
      showToast(e.message);
      return false;
    }
    setLoggedIn(true);
    closeLogin();
    if (next) navigate(next);
    else showToast('로그인되었습니다');
    return true;
  };

  // 명세 2-2. 실패하면 오류를 그대로 던져 SignupModal이 칸 옆에 알려 준다
  const register = async (form) => {
    const next = signup.next;
    await authApi.register(form);
    setLoggedIn(true);
    closeSignup();
    if (next) navigate(next);
    showToast('가입이 완료되었습니다. ' + WELCOME);
  };

  const logout = () => {
    authApi.logout();
    setLoggedIn(false);
    if (GATED[location.pathname]) navigate('/', { replace: true });
    showToast('로그아웃되었습니다');
  };

  const value = { loggedIn, openLogin, openSignup, login, logout, showToast };

  return (
    <AuthContext.Provider value={value}>
      {children}
      <LoginModal modal={modal} onClose={closeLogin} onSubmit={login} onSignup={() => openSignup(modal.next)} />
      {signup.open && (
        <SignupModal
          onClose={closeSignup}
          onSubmit={register}
          onLogin={() => { const next = signup.next; closeSignup(); openLogin(next); }}
          showToast={showToast}
        />
      )}
      <div className={'auth-toast' + (toast.show ? ' show' : '')}>{toast.msg}</div>
    </AuthContext.Provider>
  );
}

function LoginModal({ modal, onClose, onSubmit, onSignup }) {
  const [id, setId] = useState('');
  const [pw, setPw] = useState('');
  const [busy, setBusy] = useState(false);
  const firstInput = useRef(null);

  useEffect(() => {
    if (!modal.open) return undefined;
    const t = setTimeout(() => firstInput.current && firstInput.current.focus(), 0);
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => { clearTimeout(t); document.removeEventListener('keydown', onKey); };
  }, [modal.open, onClose]);

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    const ok = await onSubmit(id.trim(), pw);
    setBusy(false);
    if (ok) setPw('');
  };

  return (
    // 바깥(흐린 화면)을 눌러도 닫히지 않는다. 닫기는 ×, Esc
    <div className={'auth-modal' + (modal.open ? ' open' : '')}>
      <div className="auth-modal-box" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
        <button type="button" className="auth-modal-close" aria-label="닫기" onClick={onClose}>×</button>
        <h2 className="auth-modal-title" id="auth-modal-title">로그인</h2>
        <p className="auth-modal-sub">{modal.sub}</p>
        <form onSubmit={submit} noValidate>
          <label className="auth-field"><span>아이디</span><input ref={firstInput} type="text" placeholder="아이디를 입력하세요" autoComplete="username" value={id} onChange={(e) => setId(e.target.value)} /></label>
          <label className="auth-field"><span>비밀번호</span><input type="password" placeholder="비밀번호를 입력하세요" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} /></label>
          <button type="submit" className="auth-submit" disabled={busy}>{busy ? '로그인 중…' : '로그인'}</button>
        </form>
        <p className="auth-modal-foot">아직 계정이 없으신가요? <a onClick={onSignup}>회원가입</a></p>
      </div>
    </div>
  );
}
