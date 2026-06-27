/* Apex Web Development — front-end */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
  const telHref = p => "tel:" + String(p || "").replace(/[^\d+]/g, "");
  const fmtPhone = p => {
    const d = String(p || "").replace(/\D/g, "");
    if (d.length === 10) return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
    return p;
  };
  const CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>';

  let CONTENT = null;

  // ---------- render ----------
  function render(c) {
    const b = c.business || {}, hero = c.hero || {};
    const phone = b.phone || "";

    // nav / logo
    $("#logoName").textContent = (b.name || "Apex").split(" ")[0];
    const np = $("#navPhone");
    np.href = telHref(phone); np.querySelector("span").textContent = fmtPhone(phone);
    $("#footName").textContent = b.name || "Apex Web Development";
    $("#footTag").textContent = b.tagline || "";
    $("#formPhone").textContent = fmtPhone(phone);

    // hero
    $("#heroEyebrow").textContent = hero.eyebrow || "";
    $("#heroHeadline").innerHTML = highlight(hero.headline || "");
    $("#heroSub").textContent = hero.sub || "";
    $("#heroCta1").textContent = hero.ctaPrimary || "Get a Quote";
    $("#heroCta2").textContent = hero.ctaSecondary || "See My Work";
    const stats = [["stat1num", "stat1label"], ["stat2num", "stat2label"], ["stat3num", "stat3label"]];
    $("#heroStats").innerHTML = stats.map(([n, l]) =>
      `<div class="stat"><div class="num">${esc(hero[n] || "")}</div><div class="lbl">${esc(hero[l] || "")}</div></div>`).join("");

    // services
    $("#servicesGrid").innerHTML = (c.services || []).map((s, i) =>
      `<div class="card reveal ${i % 3 === 1 ? "d1" : i % 3 === 2 ? "d2" : ""}">
        <div class="ico">${esc(s.icon || "✦")}</div>
        <h3>${esc(s.title)}</h3><p>${esc(s.desc)}</p></div>`).join("");

    // process
    $("#stepsGrid").innerHTML = (c.process || []).map((s, i) =>
      `<div class="step reveal ${["", "d1", "d2", "d3"][i % 4]}"><div class="n">${esc(s.step)}</div><h4>${esc(s.title)}</h4><p>${esc(s.desc)}</p></div>`).join("");

    // portfolio
    $("#folioGrid").innerHTML = (c.portfolio || []).map((p, i) => folioCard(p, i)).join("");

    // pricing
    $("#priceGrid").innerHTML = (c.pricing || []).map(p => priceCard(p)).join("");
    const care = c.carePlan || {};
    $("#careWrap").innerHTML = (care.enabled === false) ? "" :
      `<div class="care reveal">
        <div><h4>${esc(care.name || "Care Plan")}</h4><p>${esc(care.blurb || "")}</p></div>
        <div style="text-align:right"><div class="ca-price">$${esc(care.price || "")}<span style="font-size:1rem;color:var(--muted)">${esc(care.period || "/mo")}</span></div>
        <a href="#contact" class="btn btn-ghost" style="margin-top:.5rem">Add to any plan</a></div></div>`;

    // about
    const ab = c.about || {};
    $("#aboutHeading").textContent = ab.heading || "";
    $("#aboutBody").textContent = ab.body || "";
    $("#aboutPoints").innerHTML = (ab.points || []).map(p =>
      `<li><span class="tick">${CHECK}</span><span>${esc(p)}</span></li>`).join("");
    $("#aboutAvatar").textContent = (b.owner || "B").charAt(0).toUpperCase();
    $("#aboutSign").textContent = `— ${b.owner || "Ben"}, ${b.name || "Apex"}`;

    // testimonials
    $("#quotesGrid").innerHTML = (c.testimonials || []).map((t, i) =>
      `<div class="qcard reveal ${["", "d1", "d2"][i % 3]}">
        <div class="stars">★★★★★</div><p>"${esc(t.quote)}"</p>
        <div class="who"><div class="a">${esc((t.name || "?").charAt(0))}</div>
        <div><div class="n">${esc(t.name)}</div><div class="r">${esc(t.role)}</div></div></div></div>`).join("");

    // faq
    $("#faqList").innerHTML = (c.faq || []).map(f =>
      `<div class="faq-item"><button class="faq-q">${esc(f.q)}<span class="pm">+</span></button>
       <div class="faq-a"><div>${esc(f.a)}</div></div></div>`).join("");

    // careers
    const careers = c.careers || [];
    $("#careersGrid").innerHTML = careers.length ? careers.map(j =>
      `<div class="career reveal"><div>
        <h4>${esc(j.title)}</h4>
        <div class="meta"><span>📍 ${esc(j.location || "Remote")}</span><span>🗂 ${esc(j.type || "Contract")}</span></div>
        <p>${esc(j.description)}</p></div>
        <a href="mailto:${esc(b.email)}?subject=${encodeURIComponent("Application: " + (j.title || ""))}" class="btn btn-ghost">Apply</a></div>`).join("")
      : `<div class="career-empty">No open positions right now — but I'm always glad to hear from talented people. Reach out any time.</div>`;

    // contact block
    const webHref = b.website ? (/^https?:\/\//.test(b.website) ? b.website : "https://" + b.website) : "";
    $("#ctaContact").innerHTML = `
      <a href="${telHref(phone)}"><span class="ci">📞</span><span>${esc(fmtPhone(phone))}<span class="sub">Call or text ${esc((b.owner || "Ben").split(" ")[0])} directly</span></span></a>
      <a href="mailto:${esc(b.email)}"><span class="ci">✉</span><span>${esc(b.email)}<span class="sub">Email me your project</span></span></a>
      ${b.website ? `<a href="${esc(webHref)}"><span class="ci">🌐</span><span>${esc(b.website)}<span class="sub">Apex on the web</span></span></a>` : ""}
      <a href="#"><span class="ci">📍</span><span>${esc(b.location)}<span class="sub">${esc(b.hours || "")}</span></span></a>`;

    // footer
    const fp = $("#footPhone"); fp.href = telHref(phone); fp.textContent = fmtPhone(phone);
    const fe = $("#footEmail"); fe.href = "mailto:" + (b.email || ""); fe.textContent = b.email || "";
    $("#footCopy").textContent = `© ${new Date().getFullYear()} ${b.name || "Apex Web Development"}. All rights reserved.`;

    // chat header
    $("#chatName").textContent = `${b.owner || "Ben"} — ${(b.name || "Apex").split(" ")[0]}`;
    $("#chatAv").textContent = (b.owner || "B").charAt(0).toUpperCase();
    document.title = `${b.name || "Apex Web Development"} | Custom Websites for Local Businesses`;

    initReveal(); initFaq();
  }

  function highlight(h) {
    // emphasize a key word with gradient
    const words = ["website", "websites", "customers", "proud", "leaders"];
    let out = esc(h);
    for (const w of words) {
      const re = new RegExp(`\\b(${w})\\b`, "i");
      if (re.test(out)) { out = out.replace(re, '<span class="grad">$1</span>'); break; }
    }
    return out;
  }

  function priceCard(p) {
    const feats = (p.features || []).map(f => `<li>${CHECK}<span>${esc(f)}</span></li>`).join("");
    return `<div class="price reveal ${p.featured ? "featured" : ""}">
      ${p.featured ? '<div class="badge">Most Popular</div>' : ""}
      <h3>${esc(p.name)}</h3><div class="blurb">${esc(p.blurb || "")}</div>
      <div class="amount"><span class="cur">$</span><span class="val">${esc(p.price)}</span><span class="per">${esc(p.period || "")}</span></div>
      <ul>${feats}</ul>
      <a href="#contact" class="btn ${p.featured ? "btn-primary" : "btn-ghost"} btn-block">${esc(p.cta || "Get started")}</a>
    </div>`;
  }

  function folioCard(p, i) {
    const accent = p.accent || "#6d8bff";
    const vis = p.image
      ? `<img src="${esc(p.image)}" alt="${esc(p.title)}">`
      : `<div class="mock" style="background:linear-gradient(150deg,${esc(accent)},${shade(accent)})">
           <div class="mockbar"><i></i><i></i><i></i></div>
           <div class="mockbody">
             <div class="ml" style="width:70%"></div>
             <div class="ml sm"></div><div class="ml sm" style="width:60%"></div>
             <div class="ml btn" style="background:rgba(255,255,255,.95)"></div>
           </div></div>`;
    const tags = (p.tags || []).map(t => `<span>${esc(t)}</span>`).join("");
    return `<div class="folio-card reveal ${["", "d1", "d2"][i % 3]}">
      <div class="folio-vis">
        <span class="style-tag" style="background:${esc(accent)}cc">${esc(p.style || "")}</span>
        ${vis}
      </div>
      <div class="folio-body">
        <div class="cat">${esc(p.category || "")}</div>
        <h3>${esc(p.title)}</h3>
        <p>${esc(p.description || "")}</p>
        <div class="folio-tags">${tags}</div>
      </div></div>`;
  }
  function shade(hex) {
    try {
      const n = parseInt(hex.slice(1), 16);
      let r = (n >> 16) - 40, g = ((n >> 8) & 255) - 30, b = (n & 255) - 10;
      r = Math.max(0, r); g = Math.max(0, g); b = Math.max(0, b);
      return `rgb(${r},${g},${b})`;
    } catch (e) { return "#222"; }
  }

  // ---------- interactions ----------
  function initFaq() {
    document.querySelectorAll(".faq-q").forEach(q => {
      q.addEventListener("click", () => {
        const item = q.closest(".faq-item");
        const a = item.querySelector(".faq-a");
        const open = item.classList.toggle("open");
        a.style.maxHeight = open ? a.scrollHeight + "px" : "0";
      });
    });
  }
  function initReveal() {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); obs.unobserve(e.target); } });
    }, { threshold: 0.12 });
    document.querySelectorAll(".reveal:not(.in)").forEach(r => obs.observe(r));
  }
  function initNav() {
    const nav = $("#nav");
    window.addEventListener("scroll", () => nav.classList.toggle("scrolled", window.scrollY > 20));
    $("#burger").addEventListener("click", () => $("#navLinks").classList.toggle("mobile-open"));
    $("#navLinks").addEventListener("click", e => { if (e.target.tagName === "A") $("#navLinks").classList.remove("mobile-open"); });
  }

  // ---------- contact form ----------
  function initForm() {
    const form = $("#leadForm"), msg = $("#formMsg");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      msg.className = "form-msg";
      const data = {
        name: $("#lf-name").value.trim(),
        email: $("#lf-email").value.trim(),
        phone: $("#lf-phone").value.trim(),
        message: $("#lf-message").value.trim()
      };
      try {
        const r = await fetch("/api/contact", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
        const j = await r.json();
        if (r.ok) {
          msg.className = "form-msg ok";
          msg.textContent = "Thanks " + (data.name.split(" ")[0] || "") + "! Your message is in — I'll get back to you very soon.";
          form.reset();
        } else {
          msg.className = "form-msg err"; msg.textContent = j.error || "Something went wrong.";
        }
      } catch (err) {
        msg.className = "form-msg err"; msg.textContent = "Network error — please call or email instead.";
      }
    });
  }

  // ---------- chat ----------
  const Chat = {
    convId: localStorage.getItem("apex_conv") || null,
    lastId: 0,
    poll: null,
    open: false,
    init() {
      $("#chatFab").addEventListener("click", () => this.toggle());
      $("#chatClose").addEventListener("click", () => this.toggle(false));
      $("#chatStart").addEventListener("click", () => this.start());
      $("#chatSend").addEventListener("click", () => this.send());
      $("#chatInput").addEventListener("keydown", e => { if (e.key === "Enter") this.send(); });
      if (this.convId) { this.showChat(); }
    },
    toggle(force) {
      this.open = force == null ? !this.open : force;
      $("#chatPanel").classList.toggle("open", this.open);
      $("#chatBadge").style.display = "none";
      if (this.open && this.convId) { this.refresh(); this.startPoll(); }
      else { this.stopPoll(); }
    },
    async start() {
      const name = $("#chatPreName").value.trim() || "Visitor";
      const email = $("#chatPreEmail").value.trim();
      try {
        const r = await fetch("/api/chat/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, email }) });
        const j = await r.json();
        this.convId = j.conv_id;
        localStorage.setItem("apex_conv", this.convId);
        localStorage.setItem("apex_name", name);
        this.showChat();
        this.addMsg({ sender: "admin", body: `Hey ${name.split(" ")[0]}! 👋 Thanks for reaching out. What can I help you with?`, ts: Date.now() / 1000 }, true);
        this.startPoll();
      } catch (e) { alert("Couldn't start chat — please call instead."); }
    },
    showChat() {
      $("#chatPre").style.display = "none";
      $("#chatBody").style.display = "flex";
      $("#chatFoot").style.display = "flex";
      this.refresh();
    },
    async refresh() {
      if (!this.convId) return;
      try {
        const r = await fetch(`/api/chat/messages?conv_id=${this.convId}&after=${this.lastId}`);
        const j = await r.json();
        (j.messages || []).forEach(m => this.addMsg(m));
      } catch (e) { }
    },
    addMsg(m, local) {
      if (m.id) this.lastId = Math.max(this.lastId, m.id);
      const body = $("#chatBody");
      const d = el("div", "msg " + (m.sender === "visitor" ? "visitor" : "admin"));
      d.innerHTML = esc(m.body) + `<div class="msg-time">${time(m.ts)}</div>`;
      body.appendChild(d);
      body.scrollTop = body.scrollHeight;
      if (!this.open && m.sender === "admin" && !local) {
        $("#chatBadge").style.display = "grid";
      }
    },
    async send() {
      const input = $("#chatInput"); const text = input.value.trim();
      if (!text || !this.convId) return;
      input.value = "";
      this.addMsg({ sender: "visitor", body: text, ts: Date.now() / 1000 }, true);
      try {
        await fetch("/api/chat/send", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conv_id: this.convId, body: text, name: localStorage.getItem("apex_name") || "" })
        });
      } catch (e) { }
    },
    startPoll() { this.stopPoll(); this.poll = setInterval(() => this.refresh(), 3500); },
    stopPoll() { if (this.poll) clearInterval(this.poll); this.poll = null; }
  };
  function time(ts) {
    const d = new Date((ts || 0) * 1000);
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  // ---------- boot ----------
  async function boot() {
    initNav(); initForm(); Chat.init();
    try {
      const r = await fetch("/api/content");
      CONTENT = await r.json();
      render(CONTENT);
    } catch (e) {
      console.error("Failed to load content", e);
    }
  }
  document.addEventListener("DOMContentLoaded", boot);
})();
