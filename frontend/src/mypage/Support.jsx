/* 마이페이지 고객센터: 자주 묻는 질문과 문의 방법.
   답의 숫자는 서버 설정과 같게 둔다 (backend/config.py 10MB·24시간, backend/auth.py 로그인 3시간).
   문의는 이메일 보내기 링크. 주소는 발송되지 않는 예시용 도메인 example.com, 실제 운영 시 팀 주소로 교체 */
const CONTACT_EMAIL = 'teamcgi_moa@example.com';
const MAIL_SUBJECT = '[MOA 문의] ';
const MAIL_BODY = '문의 내용:\n\n발생 화면:\n발생 시각:\n화면 사진 첨부:\n';
const MAIL_LINK = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(MAIL_SUBJECT)}&body=${encodeURIComponent(MAIL_BODY)}`;

const FAQ = [
  ['어떤 사진을 올릴 수 있나요?',
    'JPG·PNG 형식, 10MB 이하 사진을 올릴 수 있습니다. 상의 사진은 상의 전체가 잘 보이는 사진, 인물 사진은 상체가 정면으로 나온 사진일수록 결과가 자연스럽습니다.'],
  ['상의 영역이 잘못 잡혔어요.',
    '3단계에서 포함할 부분은 왼쪽 클릭, 뺄 부분은 오른쪽 클릭으로 점을 더 찍으면 다시 추출합니다. 경계가 조금 어긋나면 다듬기 창의 영역 추가와 영역 제거로 직접 고칠 수 있습니다.'],
  ['합성은 얼마나 걸리나요?',
    '한 장에 약 25초가 걸립니다. 앞선 합성 요청이 있으면 순서대로 처리하며, 화면에 대기 순번과 진행률이 표시됩니다. 마이페이지 설정에서 합성 완료 알림을 켜면 다른 탭에 있어도 알려 드립니다.'],
  ['저장하지 않은 결과는 어떻게 되나요?',
    '저장하지 않은 결과는 합성하기 화면의 내 작업 기록에 24시간 동안 남은 뒤 자동으로 삭제됩니다. 저장한 결과는 사진첩에 계속 보관됩니다.'],
  ['결과 사진을 내려받고 싶어요.',
    '사진첩에서 사진 아래 ⋯ 버튼을 누른 뒤 다운로드를 선택하면 됩니다. 크게 보기 화면에서도 내려받을 수 있습니다.'],
  ['로그인이 풀렸어요.',
    '로그인은 로그인한 시각부터 3시간 동안 유지됩니다. 시간이 지나면 로그인 창이 열리며, 다시 로그인하면 됩니다. 저장한 결과와 내 작업 기록은 그대로 남아 있습니다.'],
  ['올린 사진의 위치 정보가 남나요?',
    '사진을 올리면 휴대폰 회전 정보만 반영해 바로 세운 뒤 저장하며, 촬영 위치 같은 사진 속 부가 정보는 저장하지 않습니다.'],
];

export default function Support() {
  return (
    <>
      <section className="as-panel as-set">
        <h3>자주 묻는 질문</h3>
        <div className="as-faq">
          {FAQ.map(([q, a]) => (
            <details key={q}>
              <summary>{q}</summary>
              <p>{a}</p>
            </details>
          ))}
        </div>
      </section>
      <section className="as-panel as-set">
        <h3>문의하기</h3>
        <p className="as-set-desc">오류 제보와 기능 제안은 이메일로 받습니다. 화면 사진과 발생 시각을 함께 보내 주시면 빠르게 확인합니다.</p>
        <p className="as-contact">{CONTACT_EMAIL}</p>
        <a className="as-btn" href={MAIL_LINK}>이메일로 문의하기</a>
      </section>
    </>
  );
}
