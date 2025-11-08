// shared/layout.js

function setupHeaderDropdowns() {
  const wrappers = document.querySelectorAll(".dropdown-wrapper");

  wrappers.forEach(wrapper => {
    const button = wrapper.querySelector(".dropdown-toggle");
    if (!button) return;

    button.addEventListener("click", (e) => {
      e.stopPropagation();

      // đóng tất cả dropdown khác trước
      document.querySelectorAll(".dropdown-wrapper.open").forEach(other => {
        if (other !== wrapper) other.classList.remove("open");
      });

      // toggle dropdown hiện tại
      wrapper.classList.toggle("open");
    });
  });

  // click ra ngoài => đóng hết
  document.addEventListener("click", () => {
    document.querySelectorAll(".dropdown-wrapper.open").forEach(openOne => {
      openOne.classList.remove("open");
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const headerMount = document.getElementById("site-header");
  const footerMount = document.getElementById("site-footer");

  if (headerMount) {
    fetch("../shared/header.html")
      .then(res => res.text())
      .then(html => {
        headerMount.innerHTML = html;

        // gắn dropdown SAU KHI header đã render
        setupHeaderDropdowns();
      })
      .catch(err => {
        console.error("Không load được header:", err);
      });
  }

  if (footerMount) {
    fetch("../shared/footer.html")
      .then(res => res.text())
      .then(html => {
        footerMount.innerHTML = html;
      })
      .catch(err => {
        console.error("Không load được footer:", err);
      });
  }
});
