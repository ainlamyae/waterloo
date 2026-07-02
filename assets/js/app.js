(function () {
  const contentEl = document.getElementById("content");
  const navList = document.getElementById("nav-list");
  const sidebar = document.getElementById("sidebar");
  const navToggle = document.getElementById("nav-toggle");
  const navBackdrop = document.getElementById("nav-backdrop");
  const titleEl = document.getElementById("site-title");

  function parseFrontmatter(raw) {
    const m = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!m) return { meta: {}, body: raw };
    const meta = {};
    m[1].split("\n").forEach((line) => {
      const idx = line.indexOf(":");
      if (idx === -1) return;
      meta[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    });
    return { meta, body: m[2] };
  }

  function buildNav() {
    const introHeading = document.querySelector("#intro-video h2[id]");
    const sections = [introHeading, ...contentEl.querySelectorAll("h2[id]")].filter(Boolean);
    navList.innerHTML = "";
    sections.forEach((heading) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = "#" + heading.id;
      a.textContent = heading.textContent;
      li.appendChild(a);
      navList.appendChild(li);
    });
    return Array.from(sections);
  }

  function closeDrawer() {
    sidebar.classList.remove("open");
    navBackdrop.classList.remove("visible");
    navToggle.setAttribute("aria-expanded", "false");
  }

  function setupNavInteractions(sections) {
    navList.addEventListener("click", (e) => {
      const a = e.target.closest("a");
      if (!a) return;
      e.preventDefault();
      const id = a.getAttribute("href").slice(1);
      const target = document.getElementById(id);
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        history.pushState(null, "", "#" + id);
      }
      closeDrawer();
    });

    navToggle.addEventListener("click", () => {
      const isOpen = sidebar.classList.toggle("open");
      navBackdrop.classList.toggle("visible", isOpen);
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
    navBackdrop.addEventListener("click", closeDrawer);

    if (!sections.length) return;
    const links = Array.from(navList.querySelectorAll("a"));
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const link = links.find((l) => l.getAttribute("href") === "#" + entry.target.id);
          if (!link) return;
          if (entry.isIntersecting) {
            links.forEach((l) => l.classList.remove("active"));
            link.classList.add("active");
          }
        });
      },
      { rootMargin: "-90px 0px -70% 0px", threshold: 0 }
    );
    sections.forEach((s) => observer.observe(s));
  }

  function insertAirportDirections() {
    const heading = document.getElementById("section-1");
    if (!heading) return;

    const caption = document.createElement("p");
    caption.className = "video-caption";
    caption.textContent = "مسیر پیشنهادی از ترمینال ۱ فرودگاه پیرسون تورنتو تا دانشگاه واترلو:";

    const wrap = document.createElement("div");
    wrap.className = "video-wrap map-wrap section-map";
    const iframe = document.createElement("iframe");
    iframe.loading = "lazy";
    iframe.title = "مسیر فرودگاه پیرسون تورنتو (ترمینال ۱) تا دانشگاه واترلو";
    const origin = encodeURIComponent("Toronto Pearson International Airport Terminal 1");
    const destination = encodeURIComponent("University of Waterloo");
    iframe.src = `https://www.google.com/maps?saddr=${origin}&daddr=${destination}&output=embed`;
    wrap.appendChild(iframe);

    heading.after(caption, wrap);
  }

  function showError() {
    contentEl.innerHTML =
      '<div class="load-error">' +
      "<p>بارگذاری محتوا ممکن نشد.</p>" +
      "<p>این صفحه برای نمایش راهنما به یک وب‌سرور محلی نیاز دارد (به‌دلیل استفاده از fetch). " +
      "دستور زیر را در پوشه پروژه اجرا کنید و سپس آدرس http://localhost:8000 را باز کنید:</p>" +
      "<pre>python -m http.server 8000</pre>" +
      "</div>";
  }

  fetch("content/guide.md")
    .then((res) => {
      if (!res.ok) throw new Error("failed to load guide.md");
      return res.text();
    })
    .then((raw) => {
      const { meta, body } = parseFrontmatter(raw);
      if (meta.title) {
        document.title = meta.title + " | راهنمای تازه‌واردین به واترلو";
        titleEl.textContent = meta.title;
      }
      contentEl.innerHTML = MiniMarkdown.render(body);
      insertAirportDirections();
      const sections = buildNav();
      setupNavInteractions(sections);

      if (location.hash) {
        const target = document.getElementById(location.hash.slice(1));
        if (target) target.scrollIntoView({ block: "start" });
      }
    })
    .catch(showError);
})();
