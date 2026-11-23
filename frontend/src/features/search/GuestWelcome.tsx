import { useState } from "react";
import { Icon } from "../../components/Icon";

export function GuestWelcome({
  onRequestLogin,
}: {
  onRequestLogin?: () => void;
}) {
  const [paused, setPaused] = useState(false);
  return (
    <div className="guest-welcome" data-motion={paused ? "paused" : "playing"}>
      <section className="guest-banner" aria-labelledby="discover-title">
        <div className="guest-banner-copy">
          <span className="guest-kicker">MỘT Ý TƯỞNG. VÔ VÀN KHÁM PHÁ.</span>
          <h1 id="discover-title">
            Hình dung điều bạn thích.
            <br />
            <em>Để Synlens tìm thấy.</em>
          </h1>
          <p>
            Từ một chú mèo, một tách cà phê đến cả bầu trời đầy sao. Bắt đầu
            bằng vài từ và khám phá những hình ảnh dành cho cảm hứng của bạn.
          </p>
          <div className="guest-actions">
            <a
              className="guest-primary"
              href="#query"
              onClick={(event) => {
                event.preventDefault();
                document.getElementById("query")?.focus();
              }}
            >
              <Icon kind="search" />
              Thử tìm ảnh ngay
            </a>
            <a
              className="guest-secondary"
              href="/login"
              onClick={(event) => {
                if (
                  !onRequestLogin ||
                  event.metaKey ||
                  event.ctrlKey ||
                  event.shiftKey ||
                  event.altKey
                )
                  return;
                event.preventDefault();
                onRequestLogin();
              }}
            >
              Khám phá cùng Synlens
            </a>
          </div>
          <p className="guest-access-note">
            Tìm ảnh công khai ngay, không cần tài khoản.
          </p>
        </div>
        <div className="guest-visual">
          <div className="guest-orbit" aria-hidden="true" />
          <figure className="guest-photo guest-photo-space">
            <img
              src="/images/login/hubble_deep_field.jpg"
              alt="Những thiên hà giữa bầu trời sao"
              width="1000"
              height="872"
            />
            <figcaption>Một chút bao la</figcaption>
          </figure>
          <figure className="guest-photo guest-photo-coffee">
            <img
              src="/images/login/coffee.png"
              alt="Tách cà phê với lớp bọt sữa"
              width="600"
              height="400"
            />
            <figcaption>Một chút bình yên</figcaption>
          </figure>
          <figure className="guest-photo guest-photo-cat">
            <img
              src="/images/login/chelsea.png"
              alt="Chú mèo đang nhìn đầy tò mò"
              width="451"
              height="300"
            />
            <figcaption>Một chút đáng yêu</figcaption>
          </figure>
          <div className="guest-query-bubble" aria-hidden="true">
            <Icon kind="search" />
            <span>
              con mèo<span>con meo · a cat</span>
            </span>
            <span className="guest-query-spark">✦</span>
          </div>
          <button
            className="guest-motion-toggle"
            type="button"
            aria-pressed={paused}
            onClick={() => setPaused(!paused)}
          >
            {paused ? "Bật hoạt ảnh" : "Tạm dừng hoạt ảnh"}
          </button>
        </div>
      </section>
    </div>
  );
}
