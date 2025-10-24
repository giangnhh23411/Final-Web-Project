// simple horizontal scroll carousel for each .carousel

document.querySelectorAll(".carousel").forEach((carouselEl) => {
  const track = carouselEl.querySelector(".carousel-track");
  const windowEl = carouselEl.querySelector(".carousel-window");
  const leftBtn = carouselEl.querySelector(".carousel-arrow.left");
  const rightBtn = carouselEl.querySelector(".carousel-arrow.right");

  // trong track, mỗi .product-card có width cố định 200px + gap 16px
  // ta sẽ scroll theo đúng 1 card
  const getStep = () => {
    const card = track.querySelector(".product-card");
    if (!card) return 220; // fallback
    const style = window.getComputedStyle(card);
    const cardWidth = card.getBoundingClientRect().width;
    const marginRight = parseFloat(style.marginRight) || 0;
    return cardWidth + marginRight + 16; // 16 = gap flex
  };

  leftBtn.addEventListener("click", () => {
    windowEl.scrollBy({
      left: -getStep(),
      behavior: "smooth",
    });
  });

  rightBtn.addEventListener("click", () => {
    windowEl.scrollBy({
      left: getStep(),
      behavior: "smooth",
    });
  });

  // make the inner track scrollable horizontally inside windowEl
  // we actually scroll windowEl, not track
  // so ensure no scrollbar ugly:
  windowEl.style.scrollBehavior = "smooth";
  windowEl.style.overflowX = "auto";
  windowEl.style.scrollSnapType = "x mandatory";

  // snap each card
  track.querySelectorAll(".product-card").forEach((card) => {
    card.style.scrollSnapAlign = "start";
  });
});
