import { request } from './client.js';

// 명세 2-3
export function getMe() {
  return request('GET', '/me');
}

// 명세 2-7. change: { name, phone, bio } 중 바꿀 것만. 응답은 바뀐 내 정보
export function updateProfile(change) {
  return request('PATCH', '/me', change);
}

// 명세 2-8. 프로필 사진 올리기 / 기본 그림으로
export function uploadAvatar(file) {
  const form = new FormData();
  form.append('file', file);
  return request('POST', '/me/avatar', form);
}

export function resetAvatar() {
  return request('DELETE', '/me/avatar');
}

// 명세 2-9. 본인 확인용으로 지금 비밀번호를 함께 보낸다
export function changeEmail(email, password) {
  return request('PATCH', '/me/email', { email, password });
}

// 명세 2-10. 바꾸면 이 기기만 로그인 유지, 다른 기기는 로그아웃
export function changePassword(currentPassword, newPassword) {
  return request('PATCH', '/me/password', { current_password: currentPassword, new_password: newPassword });
}
