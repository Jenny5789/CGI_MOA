import { useEffect, useRef, useState } from 'react';
import landingCss from '../styles/landing-light.css?inline';
import usePageStyle from '../components/usePageStyle.js';
import TopNav, { StudioLink } from '../components/TopNav.jsx';

// 위쪽 예시: 객체(상의) 사진 + 배경(인물) 사진 -> 결과 사진. 2.6초마다 다음 예시로 넘어간다.
const SLIDES = [
  { object: '/assets/gallery/top_orange_knit.jpg', bg: '/assets/gallery/SummerCool_Female.jpg', result: '/assets/gallery/SpringWarm_Female.jpg' },
  { object: '/assets/gallery/top_lavender_cardigan.jpg', bg: '/assets/gallery/SpringWarm_Female.jpg', result: '/assets/gallery/SummerCool_Female.jpg' },
];

export default function Home() {
  usePageStyle(landingCss, 'MOA');
  const [current, setCurrent] = useState(0);
  // 뒤쪽 흐린 배경은 두 겹을 번갈아 바꿔서 부드럽게 넘어가게 한다
  const [blur, setBlur] = useState({ a: SLIDES[0].result, b: '', showA: true });

  const currentRef = useRef(0);

  const goTo = (i) => {
    currentRef.current = i;
    setCurrent(i);
    setBlur((s) => (s.showA ? { ...s, b: SLIDES[i].result, showA: false } : { ...s, a: SLIDES[i].result, showA: true }));
  };
  const goToRef = useRef(goTo);
  goToRef.current = goTo;

  useEffect(() => {
    const t = setInterval(() => goToRef.current((currentRef.current + 1) % SLIDES.length), 2600);
    return () => clearInterval(t);
  }, []);

  const slide = SLIDES[current];

  return (
    <>
      <div className="ln-bg-blur">
        <div className={'ln-bg-blur-layer' + (blur.showA ? ' active' : '')} style={blur.a ? { backgroundImage: `url(${blur.a})` } : undefined} />
        <div className={'ln-bg-blur-layer' + (!blur.showA ? ' active' : '')} style={blur.b ? { backgroundImage: `url(${blur.b})` } : undefined} />
      </div>

      <TopNav />

      <section className="ln-hero">
        <div className="ln-hero-left">
          <p className="ln-logo-text">Merge Object Atmosphere</p>
          <h1>내가 원하는 것<br />그게 무엇이든<br />미리 만나보세요</h1>
          <p className="ln-sub">사진 한 장으로,<br />더 가까워지는 새로운 가능성.</p>
          <StudioLink className="ln-btn">지금, 합성해보기 →</StudioLink>
        </div>

        <div className="ln-hero-right">
          <div className="ln-compose">
            <div className="ln-card ln-card-object ln-polaroid">
              <img src={slide.object} alt="합성할 상의" />
              <span className="ln-card-label">객체 이미지</span>
            </div>
            <div className="ln-card ln-card-bg ln-polaroid">
              <img src={slide.bg} alt="입어볼 인물" />
              <span className="ln-card-label">배경 이미지</span>
            </div>
            <div className="ln-card ln-card-result ln-polaroid ln-polaroid-plain">
              <span className="ln-tag">Make It Real</span>
              <img src={slide.result} alt="합성 결과 예시" />
              <button className="ln-generate">✦ Generate</button>
            </div>
          </div>

          <div className="ln-thumbs">
            {SLIDES.map((s, i) => (
              <div key={s.result} className={'ln-thumb-polaroid' + (i === current ? ' active' : '')} onClick={() => goTo(i)}>
                <img src={s.result} alt="" />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="ln-features" id="features">
        <p className="ln-section-eyebrow">USE CASES</p>
        <h2>MOA로 할 수 있는 것</h2>
        <div className="ln-feature-grid">
          <article className="ln-feature-card">
            <div className="ln-feature-visual"><img src="/assets/gallery/AutumnWarm_Male.jpg" alt="" /></div>
            <h3>상의 착용 합성</h3>
            <p>직접 입어보지 않아도, 마음에 드는 상의를 내 사진 위에 합성해 착용한 모습을 미리 확인합니다.</p>
          </article>
          <article className="ln-feature-card">
            <div className="ln-feature-visual"><img src="/assets/gallery/SpringWarm_Female.jpg" alt="" /></div>
            <h3>색상 변경</h3>
            <p>같은 상의를 다른 색으로 바꿔 보고, 나에게 가장 잘 어울리는 색을 골라봅니다.</p>
          </article>
          <article className="ln-feature-card">
            <div className="ln-feature-visual"><img src="/assets/samples/sample-object-person.jpg" alt="" /></div>
            <h3>코디 세트 미리보기</h3>
            <p>하의는 고정해 두고 상의만 바꿔가며, 어울리는 한 세트를 사진으로 미리 보고 고를 수 있습니다.</p>
          </article>
          <article className="ln-feature-card">
            <div className="ln-feature-visual"><img src="/assets/gallery/SummerCool_Female.jpg" alt="" /></div>
            <h3>사진첩에 저장</h3>
            <p>마음에 든 합성 결과를 사진첩에 모아두고, 언제든 다시 꺼내 비교해봅니다.</p>
          </article>
        </div>
      </section>

      <section className="ln-how" id="how">
        <p className="ln-section-eyebrow">HOW IT WORKS</p>
        <h2>세 단계면 충분해요</h2>
        <div className="ln-how-steps">
          <div className="ln-how-step">
            <span className="ln-how-no">01</span>
            <h4>사진 업로드</h4>
            <p>입어보고 싶은 상의 사진을 올려주세요.</p>
          </div>
          <div className="ln-how-step">
            <span className="ln-how-no">02</span>
            <h4>합성 대상 추출</h4>
            <p>사진에서 상의만 자동으로 깔끔하게 분리합니다.</p>
          </div>
          <div className="ln-how-step">
            <span className="ln-how-no">03</span>
            <h4>합성 결과 확인 저장</h4>
            <p>하의와 함께 코디한 결과를 바로 확인하고 사진첩에 저장하세요.</p>
          </div>
        </div>
      </section>

      <section className="ln-cta-band" id="cta">
        <h2>지금, 사진 한 장으로<br />시작해보세요.</h2>
        <StudioLink className="ln-btn">지금, 합성해보기 →</StudioLink>
      </section>
    </>
  );
}
