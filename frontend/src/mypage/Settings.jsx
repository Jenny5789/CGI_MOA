/* 마이페이지 설정 화면 두 가지.
   - AccountPanel: 내 정보의 '계정 설정'에서 고른 항목 하나 (프로필 수정, 이메일 변경, 비밀번호 변경, 명세 2-7~2-10).
     서버가 돌려준 내 정보로 상단 메뉴 프로필도 바로 바뀌도록 onMe로 넘긴다.
   - ServiceSettings: 왼쪽 '설정'. 계정과 관계없는 이 브라우저의 설정 (알림, 합성 기본 설정) */
import { useEffect, useRef, useState } from 'react';
import { changeEmail, changePassword, resetAvatar, updateProfile, uploadAvatar } from '../api/me.js';
import { PASSWORD_HINT, PHONE_HINT, normalizeEmail, normalizePhone, passwordOk } from '../auth/signupRules.js';
import { disableNotify, enableNotify, notifyEnabled, notifySupported } from '../utils/notify.js';
import { readComposeDefaults, saveComposeDefaults } from '../utils/composeDefaults.js';
import { DEFAULT_BIO } from '../utils/profile.js';

const NAME_MAX = 20; // 서버 backend/routers/auth.py NAME_MAX와 같게
const BIO_MAX = 60;
const MAX_UPLOAD = 10 * 1024 * 1024;

function Section({ id, title, desc, children }) {
  return (
    <section className="as-panel as-set" id={id}>
      <h3>{title}</h3>
      {desc && <p className="as-set-desc">{desc}</p>}
      {children}
    </section>
  );
}

function Field({ label, hint, children }) {
  return (
    <label className="as-field">
      <span className="as-field-label">{label}</span>
      {children}
      {hint && <span className="as-field-hint">{hint}</span>}
    </label>
  );
}

function ProfileForm({ me, onMe, showToast }) {
  const [form, setForm] = useState({ name: '', phone: '', bio: '' });
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    if (me) setForm({ name: me.name || '', phone: me.phone || '', bio: me.bio || '' });
  }, [me]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  // 바뀐 칸만 보낸다
  const submit = async (e) => {
    e.preventDefault();
    if (!me || busy) return;
    const change = {};
    if (form.name.trim() !== me.name) change.name = form.name;
    if (form.phone.trim() !== (me.phone || '')) change.phone = form.phone;
    if (form.bio.trim() !== (me.bio || '')) change.bio = form.bio;
    if (!Object.keys(change).length) { showToast('바뀐 내용이 없습니다.'); return; }
    if (change.name !== undefined && !form.name.trim()) { showToast('이름 입력이 필요합니다.'); return; }
    if (change.phone && normalizePhone(change.phone) === null) { showToast(`휴대폰 번호 형식은 ${PHONE_HINT}입니다.`); return; }
    setBusy(true);
    try {
      onMe(await updateProfile(change));
      showToast('프로필을 저장했습니다.');
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  const pickAvatar = async (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = ''; // 같은 파일을 다시 골라도 바뀌게
    if (!file) return;
    if (!/^image\/(jpeg|png)$/.test(file.type)) { showToast('jpg 또는 png 사진만 올릴 수 있습니다.'); return; }
    if (file.size > MAX_UPLOAD) { showToast('사진은 10MB 이하만 올릴 수 있습니다.'); return; }
    setBusy(true);
    try {
      onMe(await uploadAvatar(file));
      showToast('프로필 사진을 바꿨습니다.');
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  const clearAvatar = async () => {
    setBusy(true);
    try {
      onMe(await resetAvatar());
      showToast('기본 프로필로 바꿨습니다.');
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <div className="as-set-avatar">
        <div className="as-profile-avatar">{me && me.avatar_url && <img src={me.avatar_url} alt="" />}</div>
        <div className="as-set-avatar-info">
          <div className="as-profile-name">{me ? me.name : ''}</div>
          <div className="as-profile-email">{me ? me.email : ''}</div>
          <div className="as-set-avatar-tools">
            <button type="button" className="as-btn" disabled={busy} onClick={() => fileRef.current && fileRef.current.click()}>사진 변경</button>
            <button type="button" className="as-btn ghost" disabled={busy || !me || !me.avatar_url} onClick={clearAvatar}>기본 프로필</button>
            <input ref={fileRef} type="file" accept="image/jpeg,image/png" hidden onChange={pickAvatar} />
          </div>
        </div>
      </div>
      <div className="as-set-grid">
        <Field label="아이디"><input className="as-input" value={me ? me.username : ''} disabled /></Field>
        <Field label="이름" hint={`${form.name.trim().length} / ${NAME_MAX}자`}>
          <input className="as-input" value={form.name} maxLength={NAME_MAX} onChange={set('name')} />
        </Field>
        <Field label="휴대폰 번호">
          <input className="as-input" value={form.phone} placeholder={PHONE_HINT} inputMode="tel" onChange={set('phone')} />
        </Field>
      </div>
      <Field label="소개 글" hint={`${form.bio.trim().length} / ${BIO_MAX}자`}>
        <textarea className="as-input as-textarea" rows={2} value={form.bio} maxLength={BIO_MAX} placeholder={DEFAULT_BIO} onChange={set('bio')} />
      </Field>
      <div className="as-set-actions"><button type="submit" className="as-btn" disabled={busy}>저장</button></div>
    </form>
  );
}

function EmailForm({ me, onMe, showToast }) {
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    if (!normalizeEmail(email)) { showToast('이메일 주소 형식이 올바르지 않습니다.'); return; }
    if (!pw) { showToast('지금 비밀번호 입력이 필요합니다.'); return; }
    setBusy(true);
    try {
      onMe(await changeEmail(email, pw));
      setEmail(''); setPw('');
      showToast('이메일을 변경했습니다.');
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <div className="as-set-grid">
        <Field label="지금 이메일"><input className="as-input" value={(me && me.email) || '등록된 이메일이 없습니다.'} disabled /></Field>
        <Field label="새 이메일"><input className="as-input" type="email" value={email} autoComplete="email" onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field label="비밀번호 확인" hint="본인 확인용 지금 비밀번호입니다.">
          <input className="as-input" type="password" value={pw} autoComplete="current-password" onChange={(e) => setPw(e.target.value)} />
        </Field>
      </div>
      <div className="as-set-actions"><button type="submit" className="as-btn" disabled={busy}>이메일 변경</button></div>
    </form>
  );
}

function PasswordForm({ showToast }) {
  const [f, setF] = useState({ cur: '', next: '', again: '' });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const mismatch = f.again && f.next !== f.again;

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    if (!f.cur) { showToast('지금 비밀번호 입력이 필요합니다.'); return; }
    if (!passwordOk(f.next)) { showToast(`새 비밀번호는 ${PASSWORD_HINT}입니다.`); return; }
    if (f.next !== f.again) { showToast('새 비밀번호 확인이 일치하지 않습니다.'); return; }
    setBusy(true);
    try {
      await changePassword(f.cur, f.next);
      setF({ cur: '', next: '', again: '' });
      showToast('비밀번호를 변경했습니다. 다른 기기는 로그아웃되었습니다.');
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <div className="as-set-grid">
        <Field label="지금 비밀번호"><input className="as-input" type="password" value={f.cur} autoComplete="current-password" onChange={set('cur')} /></Field>
        <Field label="새 비밀번호" hint={`${PASSWORD_HINT}입니다.`}><input className="as-input" type="password" value={f.next} autoComplete="new-password" onChange={set('next')} /></Field>
        <Field label="새 비밀번호 확인" hint={mismatch ? '새 비밀번호와 다릅니다.' : ''}>
          <input className={'as-input' + (mismatch ? ' invalid' : '')} type="password" value={f.again} autoComplete="new-password" onChange={set('again')} />
        </Field>
      </div>
      <div className="as-set-actions"><button type="submit" className="as-btn" disabled={busy}>비밀번호 변경</button></div>
    </form>
  );
}

function NotifyForm({ showToast }) {
  const [on, setOn] = useState(notifyEnabled);
  const supported = notifySupported();

  const toggle = async () => {
    if (on) { disableNotify(); setOn(false); showToast('합성 완료 알림을 껐습니다.'); return; }
    const r = await enableNotify();
    if (r === 'on') { setOn(true); showToast('합성 완료 알림을 켰습니다.'); }
    else if (r === 'denied') showToast('브라우저에서 알림이 차단되어 있습니다. 주소창의 사이트 설정에서 알림 허용이 필요합니다.');
    else showToast('이 브라우저는 알림을 지원하지 않습니다.');
  };

  return (
    <div className="as-set-row">
      <div>
        <div className="as-set-row-title">합성 완료 알림</div>
        <div className="as-field-hint">합성이 끝났을 때 다른 탭을 보고 있으면 브라우저 알림으로 안내합니다.</div>
      </div>
      <button type="button" role="switch" aria-checked={on} aria-label="합성 완료 알림" className={'as-switch' + (on ? ' on' : '')} disabled={!supported} onClick={toggle}>
        <span />
      </button>
    </div>
  );
}

function ComposeDefaultsForm({ showToast }) {
  const [v, setV] = useState(readComposeDefaults);
  const toggle = (k, label) => () => {
    const next = { ...v, [k]: !v[k] };
    setV(next);
    saveComposeDefaults(next);
    showToast(`${label} 기본값을 ${next[k] ? '켰' : '껐'}습니다.`);
  };
  const rows = [
    ['refine', '상의 경계 보정', '지정한 상의 영역의 가장자리를 상의 윤곽에 맞게 정리합니다.'],
    ['shape', '영역 모양 유지', '지정한 합성 영역 안에서만 합성합니다. 영역보다 큰 상의는 일부가 잘릴 수 있습니다.'],
  ];
  return rows.map(([k, label, hint]) => (
    <div className="as-set-row" key={k}>
      <div>
        <div className="as-set-row-title">{label}</div>
        <div className="as-field-hint">{hint}</div>
      </div>
      <button type="button" role="switch" aria-checked={v[k]} aria-label={label} className={'as-switch' + (v[k] ? ' on' : '')} onClick={toggle(k, label)}>
        <span />
      </button>
    </div>
  ));
}

// 내 정보 상자: 상단 탭 items로 항목을 고른다. item: 'profile' / 'email' / 'password' (MyPage의 주소 #account-..., 기본 profile)
export function AccountPanel({ items, item, me, onMe, showToast }) {
  let desc = '';
  let body = <ProfileForm me={me} onMe={onMe} showToast={showToast} />;
  if (item === 'email') {
    desc = '로그인 확인과 안내에 쓰는 이메일입니다.';
    body = <EmailForm me={me} onMe={onMe} showToast={showToast} />;
  } else if (item === 'password') {
    desc = '변경하면 이 기기만 로그인 상태를 유지하고 다른 기기는 로그아웃됩니다.';
    body = <PasswordForm showToast={showToast} />;
  }
  return (
    <section className="as-panel as-set" id="account">
      <nav className="as-tabs as-account-tabs">
        {items.map(([key, t]) => (
          <a key={key} className={'as-tab' + (item === key ? ' active' : '')} href={`#account-${key}`}>{t}</a>
        ))}
      </nav>
      {desc && <p className="as-set-desc">{desc}</p>}
      {body}
    </section>
  );
}

export function ServiceSettings({ showToast }) {
  return (
    <>
      <Section id="set-notify" title="알림 설정" desc="이 브라우저에서 받을 알림입니다. 기기마다 따로 설정합니다.">
        <NotifyForm showToast={showToast} />
      </Section>
      <Section id="set-compose" title="합성 기본 설정" desc="합성 시 기본으로 선택되는 항목입니다. 합성마다 변경할 수 있습니다.">
        <ComposeDefaultsForm showToast={showToast} />
      </Section>
    </>
  );
}
