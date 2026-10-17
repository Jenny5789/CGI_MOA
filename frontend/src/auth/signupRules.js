/* 회원가입 입력 규칙 (명세 2-2). 실제 서버 backend/auth.py와 같은 규칙.
   회원가입 창이 입력하는 동안 안내할 때와, 가짜 서버(mock.js)가 검사할 때 같이 쓴다. */

export const USERNAME_HINT = '공백 없이 50자 이하';
export const PASSWORD_HINT = '8자 이상, 숫자 1개 이상 포함';
export const PHONE_HINT = '010-1234-5678';

export const usernameOk = (v) => !!v && v.length <= 50 && !/\s/.test(v);

export const passwordOk = (v) => /^(?=.*\d).{8,}$/.test(v || '');

const EMAIL_RULE = /^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$/;
// 소문자로 맞춘 이메일. 형식이 틀리면 null
export const normalizeEmail = (v) => {
  const e = (v || '').trim().toLowerCase();
  return e.length <= 255 && EMAIL_RULE.test(e) ? e : null;
};

// "010-1234-5678" 모양으로 맞춘 휴대폰 번호. 형식이 틀리면 null
export const normalizePhone = (v) => {
  const d = (v || '').replace(/[\s-]/g, '');
  if (!/^01[016789]\d{7,8}$/.test(d)) return null;
  return `${d.slice(0, 3)}-${d.slice(3, -4)}-${d.slice(-4)}`;
};
