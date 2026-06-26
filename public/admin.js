/* Apex Web Development — admin panel */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
  const api = (path, opts) => fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts)).then(async r => {
    const j = await r.json().catch(() => ({})); if (!r.ok) throw j; return j;
  });

  // ---- schema describing editable content ----
  const SECTIONS = [
    { key: "business", label: "🏢 Business Info", type: "object", help: "Your name, phone, email and the basics shown across the site.",
      fields: [
        { name: "name", t: "text" }, { name: "owner", t: "text" },
        { name: "tagline", t: "textarea" }, { name: "phone", t: "text" },
        { name: "email", t: "text" }, { name: "location", t: "text" }, { name: "hours", t: "text" }
      ] },
    { key: "hero", label: "⭐ Hero / Top", type: "object", help: "The big headline section visitors see first.",
      fields: [
        { name: "eyebrow", t: "text" }, { name: "headline", t: "textarea" }, { name: "sub", t: "textarea" },
        { name: "ctaPrimary", t: "text" }, { name: "ctaSecondary", t: "text" },
        { name: "stat1num", t: "text" }, { name: "stat1label", t: "text" },
        { name: "stat2num", t: "text" }, { name: "stat2label", t: "text" },
        { name: "stat3num", t: "text" }, { name: "stat3label", t: "text" }
      ] },
    { key: "about", label: "👤 About", type: "object",
      fields: [{ name: "heading", t: "text" }, { name: "body", t: "textarea" }, { name: "points", t: "lines" }] },
    { key: "services", label: "🛠 Services", type: "list", title: "title",
      item: [{ name: "icon", t: "text" }, { name: "title", t: "text" }, { name: "desc", t: "textarea" }] },
    { key: "process", label: "🪜 Process", type: "list", title: "title",
      item: [{ name: "step", t: "text" }, { name: "title", t: "text" }, { name: "desc", t: "textarea" }] },
    { key: "pricing", label: "💲 Pricing", type: "list", title: "name", help: "Your packages and prices. Toggle 'featured' to highlight one.",
      item: [{ name: "name", t: "text" }, { name: "price", t: "text" }, { name: "period", t: "text" },
             { name: "blurb", t: "textarea" }, { name: "features", t: "lines" }, { name: "cta", t: "text" }, { name: "featured", t: "bool" }] },
    { key: "carePlan", label: "🔧 Care Plan", type: "object",
      fields: [{ name: "name", t: "text" }, { name: "price", t: "text" }, { name: "period", t: "text" }, { name: "blurb", t: "textarea" }, { name: "enabled", t: "bool" }] },
    { key: "portfolio", label: "🖼 Work / Portfolio", type: "list", title: "title", help: "Showcase completed work. Upload a photo, or leave blank for a styled mockup.",
      item: [{ name: "title", t: "text" }, { name: "category", t: "text" }, { name: "style", t: "text" },
             { name: "description", t: "textarea" }, { name: "tags", t: "tags" }, { name: "accent", t: "color" }, { name: "image", t: "image" }] },
    { key: "testimonials", label: "💬 Testimonials", type: "list", title: "name",
      item: [{ name: "name", t: "text" }, { name: "role", t: "text" }, { name: "quote", t: "textarea" }] },
    { key: "faq", label: "❓ FAQ", type: "list", title: "q",
      item: [{ name: "q", t: "text" }, { name: "a", t: "textarea" }] },
    { key: "careers", label: "💼 Careers", type: "list", title: "title", help: "Job openings. Visitors apply by emailing you.",
      item: [{ name: "title", t: "text" }, { name: "type", t: "text" }, { name: "location", t: "text" }, { name: "description", t: "textarea" }] },
    { key: "privacy", label: "📄 Privacy Policy", type: "raw", help: "Markdown supported: ## Heading, **bold**, - bullet." }
  ];
  const LABELS = { ctaPrimary: "Primary button", ctaSecondary: "Secondary button", desc: "Description", q: "Question", a: "Answer", blurb: "Short blurb", cta: "Button text", accent: "Accent color", featured: "Featured (highlight)", enabled: "Show on site", points: "Bullet points (one per line)", features: "Features (one per line)", tags: "Tags (comma separated)" };
  const label = n => LABELS[n] || n.replace(/([A-Z])/g, " $1").replace(/^./, c => c.toUpperCase());
  const newItem = (sec) => { const o = {}; sec.item.forEach(f => o[f.name] = f.t === "bool" ? false : (f.t === "tags" ? [] : "")); return o; };

  let model = null;       // working copy of content
  let active = "inbox";   // active tab
  let curConv = null;     // open conversation id

  // ================= LOGIN =================
  $("#loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $("#loginErr"); err.textContent = "";
    try {
      await api("/api/admin/login", { method: "POST", body: JSON.stringify({ password: $("#pw").value }) });
      enterApp();
    } catch (j) { err.textContent = (j && j.error) || "Login failed."; }
  });

  async function checkSession() {
    try { await api("/api/admin/me"); enterApp(); } catch (e) { /* stay on login */ }
  }

  async function enterApp() {
    $("#loginWrap").style.display = "none";
    $("#admin").classList.add("show");
    const c = await api("/api/content");
    model = c;
    buildContentTabs();
    bindTabs();
    setTab("inbox");
    refreshBadges();
    setInterval(refreshBadges, 8000);
  }

  // ================= TABS =================
  function buildContentTabs() {
    $("#contentTabs").innerHTML = SECTIONS.map(s =>
      `<button class="tab" data-tab="${s.key}">${s.label}</button>`).join("");
  }
  function bindTabs() {
    $$(".tab[data-tab]").forEach(t => t.addEventListener("click", () => setTab(t.dataset.tab)));
    $("#logoutBtn").addEventListener("click", async () => {
      try { await api("/api/admin/logout", { method: "POST" }); } catch (e) {}
      location.reload();
    });
  }
  function setTab(key) {
    active = key;
    $$(".tab[data-tab]").forEach(t => t.classList.toggle("active", t.dataset.tab === key));
    if (key === "inbox") return renderInbox();
    if (key === "leads") return renderLeads();
    if (key === "settings") return renderSettings();
    renderSection(SECTIONS.find(s => s.key === key));
  }

  // ================= CONTENT EDITOR =================
  function header(title, sub) {
    return `<div class="main-head"><div><h2>${esc(title)}</h2>${sub ? `<p>${esc(sub)}</p>` : ""}</div></div>`;
  }
  function saveBar() {
    return `<div class="save-bar"><button class="btn btn-primary btn-lg" id="saveBtn">Save changes</button>
      <span class="saved-flash" id="savedFlash">✓ Saved & live</span>
      <a class="btn btn-ghost" href="/" target="_blank">Preview site ↗</a></div>`;
  }
  function renderSection(sec) {
    const main = $("#main");
    if (sec.type === "raw") {
      main.innerHTML = header(sec.label.replace(/^.\s/, ""), sec.help) +
        `<div class="ed-field"><textarea id="rawText" style="min-height:60vh">${esc(model[sec.key] || "")}</textarea></div>` + saveBar();
      $("#rawText").addEventListener("input", e => model[sec.key] = e.target.value);
    } else if (sec.type === "object") {
      model[sec.key] = model[sec.key] || {};
      main.innerHTML = header(sec.label.replace(/^.\s/, ""), sec.help) +
        `<div class="ed-card">${sec.fields.map(f => fieldHtml(f, model[sec.key][f.name], sec.key + "." + f.name)).join("")}</div>` + saveBar();
      bindFields(main, sec.key, sec.fields, () => model[sec.key]);
    } else if (sec.type === "list") {
      model[sec.key] = model[sec.key] || [];
      main.innerHTML = header(sec.label.replace(/^.\s/, ""), sec.help) +
        `<div id="listWrap">${model[sec.key].map((it, i) => cardHtml(sec, it, i)).join("")}</div>` +
        `<button class="add-btn" id="addItem">+ Add ${sec.label.replace(/^.\s/, "").replace(/s$/, "")}</button>` + saveBar();
      bindList(sec);
    }
    $("#saveBtn").addEventListener("click", save);
  }

  function cardHtml(sec, it, i) {
    const t = it[sec.title] || ("Item " + (i + 1));
    const fields = sec.item.map(f => fieldHtml(f, it[f.name], i + "." + f.name)).join("");
    // group some fields side by side for compactness
    return `<div class="ed-card" data-idx="${i}">
      <div class="ed-card-head"><span class="idx">${esc(t || ("#" + (i + 1)))}</span>
        <button class="icon-btn" data-remove="${i}">Remove</button></div>${fields}</div>`;
  }

  function fieldHtml(f, val, path) {
    const id = "fld_" + path.replace(/\W/g, "_");
    if (f.t === "bool") {
      return `<div class="ed-field"><label class="switch"><input type="checkbox" data-path="${path}" data-type="bool" ${val ? "checked" : ""}><span class="track"></span> <span>${esc(label(f.name))}</span></label></div>`;
    }
    if (f.t === "textarea") {
      return `<div class="ed-field"><label>${esc(label(f.name))}</label><textarea data-path="${path}">${esc(val || "")}</textarea></div>`;
    }
    if (f.t === "lines") {
      const txt = Array.isArray(val) ? val.join("\n") : (val || "");
      return `<div class="ed-field"><label>${esc(label(f.name))}</label><textarea data-path="${path}" data-type="lines" placeholder="One per line">${esc(txt)}</textarea></div>`;
    }
    if (f.t === "tags") {
      const txt = Array.isArray(val) ? val.join(", ") : (val || "");
      return `<div class="ed-field"><label>${esc(label(f.name))}</label><input type="text" data-path="${path}" data-type="tags" value="${esc(txt)}" placeholder="Tag1, Tag2"></div>`;
    }
    if (f.t === "color") {
      const v = val || "#6d8bff";
      return `<div class="ed-field"><label>${esc(label(f.name))}</label><div class="color-edit">
        <input type="color" data-path="${path}" data-type="color" value="${esc(v)}">
        <input type="text" data-path="${path}" data-mirror value="${esc(v)}" style="max-width:140px"></div></div>`;
    }
    if (f.t === "image") {
      const thumb = val ? `<img class="thumb" src="${esc(val)}" alt="">` : `<div class="thumb empty">No photo</div>`;
      return `<div class="ed-field"><label>${esc(label(f.name))}</label><div class="img-edit">
        ${thumb}
        <div>
          <input type="file" accept="image/*" data-upload="${path}" style="display:none" id="${id}_file">
          <button type="button" class="btn btn-ghost" data-trigger="${id}_file">${val ? "Replace photo" : "Upload photo"}</button>
          ${val ? `<button type="button" class="icon-btn" data-clearimg="${path}" style="margin-left:.5rem">Remove</button>` : ""}
          <input type="text" data-path="${path}" value="${esc(val || "")}" placeholder="…or paste an image URL" style="margin-top:.6rem">
        </div></div></div>`;
    }
    // text / default
    return `<div class="ed-field"><label>${esc(label(f.name))}</label><input type="text" data-path="${path}" value="${esc(val || "")}"></div>`;
  }

  // bind inputs for object section
  function bindFields(scope, key, fields, getObj) {
    bindInputs(scope, (path, value) => { getObj()[lastKey(path)] = value; });
  }
  // bind list interactions
  function bindList(sec) {
    const wrap = $("#listWrap");
    bindInputs($("#main"), (path, value) => {
      const [idx, name] = splitIdxPath(path);
      model[sec.key][idx][name] = value;
    });
    // remove
    $$("[data-remove]").forEach(b => b.addEventListener("click", () => {
      model[sec.key].splice(+b.dataset.remove, 1); renderSection(sec);
    }));
    // add
    $("#addItem").addEventListener("click", () => {
      model[sec.key].push(newItem(sec)); renderSection(sec);
    });
    bindImageHandlers(sec);
    // re-bind save (renderSection adds it after)
  }

  // generic input binding: text/textarea/bool/lines/tags/color/mirror
  function bindInputs(scope, setter) {
    $$("[data-path]", scope).forEach(inp => {
      const type = inp.dataset.type;
      const ev = (inp.type === "checkbox" || inp.type === "color") ? "change" : "input";
      inp.addEventListener(ev, () => {
        let v;
        if (type === "bool") v = inp.checked;
        else if (type === "lines") v = inp.value.split("\n").map(s => s.trim()).filter(Boolean);
        else if (type === "tags") v = inp.value.split(",").map(s => s.trim()).filter(Boolean);
        else v = inp.value;
        setter(inp.dataset.path, v);
        // mirror color picker <-> text
        if (type === "color") { const m = $(`[data-mirror][data-path="${cssEsc(inp.dataset.path)}"]`); if (m) m.value = inp.value; }
        if (inp.dataset.mirror !== undefined) { const c = $(`input[type=color][data-path="${cssEsc(inp.dataset.path)}"]`); if (c) c.value = inp.value; }
      });
    });
  }
  function bindImageHandlers(sec) {
    $$("[data-trigger]").forEach(b => b.addEventListener("click", () => $("#" + b.dataset.trigger).click()));
    $$("[data-clearimg]").forEach(b => b.addEventListener("click", () => {
      setByPath(b.dataset.clearimg); renderSection(sec);
    }));
    $$("[data-upload]").forEach(inp => inp.addEventListener("change", async () => {
      const file = inp.files[0]; if (!file) return;
      if (file.size > 8 * 1024 * 1024) return alert("Image too large (max 8MB).");
      const dataUrl = await toDataUrl(file);
      try {
        const j = await api("/api/admin/upload", { method: "POST", body: JSON.stringify({ data: dataUrl }) });
        setByPathVal(inp.dataset.upload, j.url);
        renderSection(sec);
      } catch (e) { alert((e && e.error) || "Upload failed."); }
    }));
  }
  function setByPath(path) { setByPathVal(path, ""); }
  function setByPathVal(path, val) {
    const sec = SECTIONS.find(s => s.key === active);
    if (sec.type === "list") { const [idx, name] = splitIdxPath(path); model[sec.key][idx][name] = val; }
    else model[sec.key][lastKey(path)] = val;
  }
  const lastKey = p => p.split(".").slice(1).join(".");
  function splitIdxPath(p) { const parts = p.split("."); return [parseInt(parts[0], 10), parts.slice(1).join(".")]; }
  const cssEsc = s => s.replace(/(["\\.])/g, "\\$1");
  const toDataUrl = file => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file); });

  async function save() {
    const btn = $("#saveBtn"); btn.disabled = true; btn.textContent = "Saving…";
    try {
      await api("/api/admin/content", { method: "POST", body: JSON.stringify({ content: model }) });
      const f = $("#savedFlash"); f.classList.add("show"); setTimeout(() => f.classList.remove("show"), 2200);
    } catch (e) { alert((e && e.error) || "Save failed."); }
    btn.disabled = false; btn.textContent = "Save changes";
  }

  // ================= INBOX =================
  async function renderInbox() {
    $("#main").innerHTML = header("Chat Inbox", "Live messages from visitors. Click a conversation to read and reply.") +
      `<div class="inbox"><div class="conv-list" id="convList"><div class="empty-state" style="padding:2rem">Loading…</div></div>
        <div class="thread" id="thread"><div class="thread-empty">Select a conversation to start replying.</div></div></div>`;
    await loadConvs();
  }
  async function loadConvs(keepThread) {
    let data;
    try { data = await api("/api/admin/conversations"); } catch (e) { return; }
    const list = $("#convList"); if (!list) return;
    if (!data.conversations.length) { list.innerHTML = `<div class="empty-state"><div class="big">💬</div>No chats yet.<br><small>When a visitor messages you, it appears here.</small></div>`; return; }
    list.innerHTML = data.conversations.map(cv => `
      <div class="conv ${cv.id === curConv ? "active" : ""}" data-cid="${cv.id}">
        <div class="cn"><strong>${esc(cv.name || "Visitor")}</strong>${cv.unread ? '<span class="dot"></span>' : ""}</div>
        <div class="prev">${esc(cv.last_msg || "")}</div>
        ${cv.email ? `<div class="em">${esc(cv.email)}</div>` : ""}
      </div>`).join("");
    $$(".conv").forEach(c => c.addEventListener("click", () => openConv(c.dataset.cid)));
    if (curConv && !keepThread) openConv(curConv, true);
  }
  let threadPoll = null;
  async function openConv(cid, silent) {
    curConv = cid;
    $$(".conv").forEach(c => c.classList.toggle("active", c.dataset.cid === cid));
    const data = await api("/api/admin/conversation?conv_id=" + encodeURIComponent(cid));
    const info = data.info || {};
    $("#thread").innerHTML = `
      <div class="thread-head">${esc(info.name || "Visitor")}<small>${esc(info.email || "no email provided")}</small></div>
      <div class="thread-body" id="threadBody"></div>
      <div class="thread-foot"><input id="replyInput" placeholder="Type your reply…" autocomplete="off">
        <button class="btn btn-primary" id="replyBtn">Send</button></div>`;
    paintMsgs(data.messages);
    $("#replyBtn").addEventListener("click", sendReply);
    $("#replyInput").addEventListener("keydown", e => { if (e.key === "Enter") sendReply(); });
    if (!silent) $("#replyInput").focus();
    if (threadPoll) clearInterval(threadPoll);
    threadPoll = setInterval(async () => {
      if (active !== "inbox" || !curConv) return;
      try { const d = await api("/api/admin/conversation?conv_id=" + encodeURIComponent(curConv)); paintMsgs(d.messages); } catch (e) {}
    }, 4000);
    refreshBadges();
  }
  function paintMsgs(msgs) {
    const body = $("#threadBody"); if (!body) return;
    const atBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 60;
    body.innerHTML = msgs.map(m => `<div class="msg ${m.sender === "visitor" ? "admin" : "visitor"}" style="${m.sender === "visitor" ? "align-self:flex-start" : "align-self:flex-end"}">${esc(m.body)}<div class="msg-time">${ftime(m.ts)}</div></div>`).join("");
    if (atBottom) body.scrollTop = body.scrollHeight;
  }
  async function sendReply() {
    const inp = $("#replyInput"); const text = inp.value.trim(); if (!text || !curConv) return;
    inp.value = "";
    try {
      await api("/api/admin/reply", { method: "POST", body: JSON.stringify({ conv_id: curConv, body: text }) });
      const d = await api("/api/admin/conversation?conv_id=" + encodeURIComponent(curConv));
      paintMsgs(d.messages); loadConvs(true);
    } catch (e) { alert("Failed to send."); }
  }

  // ================= LEADS =================
  async function renderLeads() {
    $("#main").innerHTML = header("Quote Requests", "Messages sent through your contact form.") + `<div id="leadList"><div class="empty-state">Loading…</div></div>`;
    let data; try { data = await api("/api/admin/leads"); } catch (e) { return; }
    const wrap = $("#leadList");
    if (!data.leads.length) { wrap.innerHTML = `<div class="empty-state"><div class="big">📥</div>No quote requests yet.</div>`; return; }
    wrap.innerHTML = data.leads.map(l => `
      <div class="lead ${l.handled ? "handled" : ""}">
        <div class="lh"><strong>${esc(l.name)}</strong><span class="when">${ftime(l.ts, true)}</span></div>
        <div class="meta">${l.email ? `✉ <a href="mailto:${esc(l.email)}">${esc(l.email)}</a>&nbsp;&nbsp;` : ""}${l.phone ? `📞 <a href="tel:${esc(l.phone)}">${esc(l.phone)}</a>` : ""}</div>
        ${l.message ? `<div class="msg">${esc(l.message)}</div>` : ""}
        <label class="switch" style="margin-top:1rem"><input type="checkbox" data-lead="${l.id}" ${l.handled ? "checked" : ""}><span class="track"></span> <span>Marked as handled</span></label>
      </div>`).join("");
    $$("[data-lead]").forEach(c => c.addEventListener("change", async () => {
      await api("/api/admin/lead_handled", { method: "POST", body: JSON.stringify({ id: +c.dataset.lead, handled: c.checked }) });
      c.closest(".lead").classList.toggle("handled", c.checked); refreshBadges();
    }));
  }

  // ================= SETTINGS =================
  function renderSettings() {
    $("#main").innerHTML = header("Settings", "Manage your admin account.") +
      `<div class="ed-card" style="max-width:520px">
        <h3 style="font-family:var(--display);margin-bottom:1rem">Change password</h3>
        <div class="ed-field"><label>Current password</label><input type="password" id="curPw"></div>
        <div class="ed-field"><label>New password (min 8 chars)</label><input type="password" id="newPw"></div>
        <div class="ed-field"><label>Confirm new password</label><input type="password" id="newPw2"></div>
        <button class="btn btn-primary" id="changePwBtn">Update password</button>
        <div id="pwMsg" style="margin-top:1rem;font-size:.9rem"></div>
      </div>
      <div class="ed-card" style="max-width:520px">
        <h3 style="font-family:var(--display);margin-bottom:.6rem">About this site</h3>
        <p style="color:var(--muted);font-size:.93rem">Everything you edit here saves instantly to your live website. Your data lives in <code>apex.db</code> and uploaded photos in the <code>uploads/</code> folder.</p>
      </div>`;
    $("#changePwBtn").addEventListener("click", async () => {
      const msg = $("#pwMsg"); msg.style.color = "#ff9a9a";
      const cur = $("#curPw").value, n1 = $("#newPw").value, n2 = $("#newPw2").value;
      if (n1 !== n2) { msg.textContent = "New passwords don't match."; return; }
      try {
        await api("/api/admin/password", { method: "POST", body: JSON.stringify({ current: cur, new: n1 }) });
        msg.style.color = "var(--accent)"; msg.textContent = "✓ Password updated.";
        $("#curPw").value = $("#newPw").value = $("#newPw2").value = "";
      } catch (e) { msg.textContent = (e && e.error) || "Failed to update."; }
    });
  }

  // ================= BADGES =================
  async function refreshBadges() {
    try {
      const d = await api("/api/admin/unread_count");
      const pi = $("#pillInbox"), pl = $("#pillLeads");
      if (pi) { pi.textContent = d.unread; pi.classList.toggle("show", d.unread > 0); }
      if (pl) { pl.textContent = d.leads; pl.classList.toggle("show", d.leads > 0); }
      if (active === "inbox" && curConv) loadConvs(true);
    } catch (e) {}
  }

  function ftime(ts, withDate) {
    const d = new Date((ts || 0) * 1000);
    const t = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    return withDate ? d.toLocaleDateString([], { month: "short", day: "numeric" }) + " · " + t : t;
  }

  checkSession();
})();
