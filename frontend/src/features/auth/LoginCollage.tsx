const photos = [
  "coffee.png",
  "chelsea.png",
  "rocket.jpg",
  "hubble_deep_field.jpg",
  "camera.png",
  "grass.png",
  "brick.png",
];
const columns = [0, 3, 1, 5, 2, 4, 6];

/** Public sample artwork only; anonymous visitors never fetch private library images. */
export function LoginCollage() {
  return (
    <div className="login-collage" aria-hidden="true">
      <div className="collage-columns">
        {columns.map((offset, column) => (
          <div className="collage-column" key={offset}>
            <div className="collage-track">
              {[0, 1].map((copy) => (
                <div className="collage-group" key={copy}>
                  {[0, 1, 2, 3].map((row) => (
                    <img
                      key={row}
                      src={`/images/login/${photos[(offset + row * 2) % photos.length]}`}
                      alt=""
                      width={300}
                      height={400}
                      decoding="async"
                      fetchPriority={
                        copy === 0 && row === 0 && column < 3 ? "high" : "low"
                      }
                      draggable={false}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="collage-shade" />
    </div>
  );
}
