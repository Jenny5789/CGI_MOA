/* 회원가입 창 (명세 2-2, 2-6).
   필수: 아이디(중복확인), 비밀번호, 비밀번호 확인, 이메일 / 선택: 전화번호.
   이메일은 인증 메일을 보내지 않지만, 형식이 맞아야 하고 한 이메일로 한 번만 가입할 수 있다 (서버가 확인).
   창이 열릴 때마다 새로 그려서(AuthContext에서 열려 있을 때만 렌더) 입력값이 처음 상태로 시작한다. */
import { useEffect, useRef, useState } from 'react';
import * as authApi from '../api/auth.js';
import { normalizeEmail, normalizePhone, passwordOk, usernameOk, PASSWORD_HINT, PHONE_HINT, USERNAME_HINT } from './signupRules.js';

const EMPTY = { username: '', password: '', password2: '', email: '', phone: '' };

export default function SignupModal({ onClose, onSubmit, onLogin, showToast }) {
  const [form, setForm] = useState(EMPTY);
  const [checked, setChecked] = useState({ name: '', available: null }); // 중복확인한 아이디와 결과
  const [checking, setChecking] = useState(false);
  const [touched, setTouched] = useState({}); // 칸을 한 번 벗어났으면 형식 오류를 보여 준다
  const [tried, setTried] = useState(false); // 가입하기를 눌렀으면 빈 칸도 알려 준다
  const [serverErr, setServerErr] = useState({}); // 서버가 알려 준 칸별 오류 (이미 가입된 이메일 등)
  const [busy, setBusy] = useState(false);
  const firstInput = useRef(null);

  useEffect(() => {
    const t = setTimeout(() => firstInput.current && firstInput.current.focus(), 0);
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => { clearTimeout(t); document.removeEventListener('keydown', onKey); };
  }, [onClose]);

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    if (serverErr[key]) setServerErr((s) => ({ ...s, [key]: '' }));
  };
  const blur = (key) => () => setTouched((t) => ({ ...t, [key]: true }));
  const shown = (key) => tried || touched[key];

  const username = form.username.trim();
  const email = normalizeEmail(form.email);
  const phone = form.phone.trim() ? normalizePhone(form.phone) : '';
  const usernameAvailable = checked.name === username && checked.available === true; // 지금 칸의 아이디로 확인했는지

  const errors = {
    username: !username ? (tried ? '아이디를 입력해 주세요.' : '')
      : !usernameOk(username) ? `아이디는 ${USERNAME_HINT}로 입력해 주세요.`
        : checked.name === username && checked.available === false ? '이미 사용 중인 아이디입니다.'
          : tried && !usernameAvailable ? '아이디 중복확인을 해 주세요.' : '',
    password: !form.password ? (tried ? '비밀번호를 입력해 주세요.' : '')
      : shown('password') && !passwordOk(form.password) ? `비밀번호는 ${PASSWORD_HINT}해야 합니다.` : '',
    password2: !form.password2 ? (tried ? '비밀번호를 한 번 더 입력해 주세요.' : '')
      : (shown('password2') || form.password2.length >= form.password.length) && form.password2 !== form.password ? '비밀번호가 일치하지 않습니다.' : '',
    email: serverErr.email || (!form.email.trim() ? (tried ? '이메일을 입력해 주세요.' : '')
      : shown('email') && !email ? '올바른 이메일 주소를 입력해 주세요.' : ''),
    phone: serverErr.phone || (form.phone.trim() && shown('phone') && !phone ? `휴대폰 번호를 ${PHONE_HINT} 형식으로 입력해 주세요.` : ''),
  };
  const valid = usernameOk(username) && usernameAvailable && passwordOk(form.password) && form.password2 === form.password
    && !!email && phone !== null && !serverErr.email;

  const check = async () => {
    if (!usernameOk(username) || checking) return;
    setChecking(true);
    try {
      const res = await authApi.checkUsername(username);
      setChecked({ name: res.username, available: res.available });
    } catch (e) {
      showToast(e.message);
    }
    setChecking(false);
  };

  const submit = async (e) => {
    e.preventDefault();
    setTried(true);
    if (!valid || busy) return;
    setBusy(true);
    try {
      await onSubmit({ username, password: form.password, email, ...(phone ? { phone } : {}) });
      return; // 성공하면 AuthContext가 창을 닫는다
    } catch (err) {
      if (err.code === 'DUPLICATE_USERNAME') setChecked({ name: username, available: false });
      else if (err.code === 'DUPLICATE_EMAIL' || err.code === 'INVALID_EMAIL') setServerErr({ email: err.message });
      else if (err.code === 'INVALID_PHONE') setServerErr({ phone: err.message });
      else showToast(err.message);
    }
    setBusy(false);
  };

  const msg = (key, okText) => {
    if (errors[key]) return <small className="auth-msg error" role="alert">{errors[key]}</small>;
    if (okText) return <small className="auth-msg ok">{okText}</small>;
    return null;
  };

  return (
    <div className="auth-modal auth-modal-signup open" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="auth-modal-box" role="dialog" aria-modal="true" aria-labelledby="signup-modal-title">
        <button type="button" className="auth-modal-close" aria-label="닫기" onClick={onClose}>×</button>
        <h2 className="auth-modal-title" id="signup-modal-title">회원가입</h2>
        <p className="auth-modal-sub">MOA에서 사용할 계정을 만듭니다.</p>
        <form onSubmit={submit} noValidate>
          <div className="auth-field">
            <label htmlFor="signup-username"><span>아이디</span></label>
            <div className="auth-field-row">
              <input
                id="signup-username" ref={firstInput} type="text" placeholder={USERNAME_HINT} autoComplete="username"
                className={errors.username ? 'invalid' : ''} value={form.username} onChange={set('username')}
              />
              <button type="button" className="auth-check-btn" disabled={!usernameOk(username) || checking} onClick={check}>
                {checking ? '확인 중…' : '중복확인'}
              </button>
            </div>
            {msg('username', usernameAvailable ? '사용할 수 있는 아이디입니다.' : '')}
          </div>

          <label className="auth-field">
            <span>비밀번호</span>
            <input
              type="password" placeholder={PASSWORD_HINT} autoComplete="new-password"
              className={errors.password ? 'invalid' : ''} value={form.password} onChange={set('password')} onBlur={blur('password')}
            />
            {msg('password')}
          </label>

          <label className="auth-field">
            <span>비밀번호 확인</span>
            <input
              type="password" placeholder="비밀번호를 한 번 더 입력하세요" autoComplete="new-password"
              className={errors.password2 ? 'invalid' : ''} value={form.password2} onChange={set('password2')} onBlur={blur('password2')}
            />
            {msg('password2', form.password2 && form.password2 === form.password ? '비밀번호가 일치합니다.' : '')}
          </label>

          <label className="auth-field">
            <span>이메일</span>
            <input
              type="email" placeholder="example@email.com" autoComplete="email"
              className={errors.email ? 'invalid' : ''} value={form.email} onChange={set('email')} onBlur={blur('email')}
            />
            {msg('email')}
          </label>

          <label className="auth-field">
            <span>전화번호 <em className="auth-optional">(선택)</em></span>
            <input
              type="tel" placeholder={PHONE_HINT} autoComplete="tel"
              className={errors.phone ? 'invalid' : ''} value={form.phone} onChange={set('phone')} onBlur={blur('phone')}
            />
            {msg('phone')}
          </label>

          <button type="submit" className="auth-submit" disabled={busy}>{busy ? '가입 중…' : '가입하기'}</button>
        </form>
        <p className="auth-modal-foot">이미 계정이 있으신가요? <a onClick={onLogin}>로그인</a></p>
      </div>
    </div>
  );
}
