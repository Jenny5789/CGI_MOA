import { useEffect, useRef, useState } from 'react';
import landingCss from '../styles/landing-light.css?inline';
import usePageStyle from '../components/usePageStyle.js';
import TopNav, { StudioLink } from '../components/TopNav.jsx';
import { curatedBackgrounds, curatedResults, featureLifestyle, showcaseTops } from '../data/generatedAssets.js';

// 위쪽 예시: 객체(상의) 사진 + 배경(인물) 사진 -> 결과 사진. 5.2초마다 다음 예시로 넘어간다.
// 대표 예시는 같은 번호의 상의/모델/결과를 하나의 검증된 세트로 묶는다.
const SLIDES = curatedResults.map((result, i) => ({
  object: showcaseTops[i],
  bg: curatedBackgrounds[i],
  result,
}));

const HERO_LINES = ['내가 원하는 것', '그게 무엇이든', '미리 만나보세요'];

// 스크롤 연출: .ln-reveal 요소가 화면에 들어오면 is-in을 붙여 아래에서 떠오르게 한다 (한 번만)
function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('.ln-reveal');
    if (!('IntersectionObserver' in window)) {
      els.forEach((el) => el.classList.add('is-in'));
      return undefined;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        io.unobserve(entry.target);
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

export default function Home() {
  usePageStyle(landingCss, 'MOA');
  useReveal();
  const [current, setCurrent] = useState(0);
  const currentRef = useRef(0);
  const transitionRef = useRef(0);

  const preloadSlide = (slide) => Promise.all(
    [slide.object, slide.bg, slide.result].map((src) => new Promise((resolve) => {
      const image = new Image();
      image.onload = resolve;
      image.onerror = resolve;
      image.src = src;
    })),
  );

  const goTo = (i) => {
    const transitionId = transitionRef.current + 1;
    transitionRef.current = transitionId;
    preloadSlide(SLIDES[i]).then(() => {
      if (transitionId !== transitionRef.current) return;
      currentRef.current = i;
      setCurrent(i);
    });
  };
  const goToRef = useRef(goTo);
  goToRef.current = goTo;

  useEffect(() => {
    const t = setInterval(() => goToRef.current((currentRef.current + 1) % SLIDES.length), 5200);
    return () => clearInterval(t);
  }, []);

  const slide = SLIDES[current];

  return (
    <>
      <div className="ln-bg-blur" aria-hidden="true" />

      <TopNav />

      <section className="ln-hero">
        <div className="ln-hero-left">
          <p className="ln-logo-text">Merge Object Atmosphere</p>
          {/* 제목은 한 줄씩 아래에서 올라온다 (글자는 그대로) */}
          <h1 aria-label={HERO_LINES.join(' ')}>
            {HERO_LINES.map((line, i) => (
              <span className="ln-line" key={line} aria-hidden="true"><span style={{ '--i': i }}>{line}</span></span>
            ))}
          </h1>
          <p className="ln-sub">사진 한 장으로,<br />더 가까워지는 새로운 가능성.</p>
          <StudioLink className="ln-btn">지금, 합성해보기 →</StudioLink>
        </div>

        <div className="ln-hero-right">
          <div className="ln-compose">
            <div className="ln-card ln-card-object ln-polaroid">
              <img key={slide.object} src={slide.object} alt="합성할 상의" />
              <span className="ln-card-label">객체 이미지</span>
            </div>
            <div className="ln-card ln-card-bg ln-polaroid">
              <img key={slide.bg} src={slide.bg} alt="입어볼 인물" />
              <span className="ln-card-label">배경 이미지</span>
            </div>
            <div className="ln-card ln-card-result ln-polaroid ln-polaroid-plain">
              <span className="ln-tag">Make It Real</span>
              <img key={slide.result} src={slide.result} alt="합성 결과 예시" />
            </div>
          </div>
        </div>
      </section>

      <section className="ln-features" id="features">
        <p className="ln-section-eyebrow ln-reveal">USE CASES</p>
        <h2 className="ln-reveal">MOA로 할 수 있는 것</h2>
        <div className="ln-feature-grid">
          <article className="ln-feature-card ln-reveal" style={{ '--d': '0.00s' }}>
            <div className="ln-feature-visual"><img src={featureLifestyle[0]} alt="" /></div>
            <h3>상의 입어보기</h3>
            <p>직접 입어보지 않아도, 마음에 드는 상의를 내 사진 위에 합성해 착용한 모습을 미리 확인합니다.</p>
          </article>
          <article className="ln-feature-card ln-reveal" style={{ '--d': '0.12s' }}>
            <div className="ln-feature-visual"><img src={featureLifestyle[1]} alt="" /></div>
            <h3>사진 분위기 그대로</h3>
            <p>카페, 여행지에서 찍은 내 사진의 장소와 분위기는 그대로 두고, 상의만 바꿔 입은 모습을 만듭니다.</p>
          </article>
          <article className="ln-feature-card ln-reveal" style={{ '--d': '0.24s' }}>
            <div className="ln-feature-visual"><img src={featureLifestyle[2]} alt="" /></div>
            <h3>사진첩에 저장</h3>
            <p>마음에 든 합성 결과를 사진첩에 모아두고, 언제든 다시 꺼내 비교해봅니다.</p>
          </article>
        </div>
      </section>

      <section className="ln-how" id="how">
        <p className="ln-section-eyebrow ln-reveal">HOW IT WORKS</p>
        <h2 className="ln-reveal">세 단계면 충분해요</h2>
        <div className="ln-how-steps">
          <div className="ln-how-step ln-reveal" style={{ '--d': '0.00s' }}>
            <span className="ln-how-no">01</span>
            <h4>사진 두 장 고르기</h4>
            <p>입어볼 상의 사진과 내 인물 사진을 고르세요. 예시 사진으로 바로 해볼 수도 있어요.</p>
          </div>
          <div className="ln-how-step ln-reveal" style={{ '--d': '0.12s' }}>
            <span className="ln-how-no">02</span>
            <h4>점 찍어 영역 지정</h4>
            <p>상의와 입힐 자리에 점을 몇 번 찍으면 AI가 영역을 찾아내요.</p>
          </div>
          <div className="ln-how-step ln-reveal" style={{ '--d': '0.24s' }}>
            <span className="ln-how-no">03</span>
            <h4>합성하고 저장</h4>
            <p>잠시 뒤 나온 결과가 마음에 들면 사진첩에 저장해 언제든 다시 보세요.</p>
          </div>
        </div>
      </section>

      <section className="ln-cta-band" id="cta">
        <h2 className="ln-reveal">지금, 사진 한 장으로<br />시작해보세요.</h2>
        <div className="ln-reveal" style={{ '--d': '.15s' }}>
          <StudioLink className="ln-btn">지금, 합성해보기 →</StudioLink>
        </div>
      </section>
    </>
  );
}
