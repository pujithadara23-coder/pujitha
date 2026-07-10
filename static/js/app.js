/* ── AI Water Intake Advisor – frontend logic ───────────────────────────── */

(function () {
  "use strict";

  const form          = document.getElementById("waterForm");
  const submitBtn     = document.getElementById("submitBtn");
  const btnText       = submitBtn.querySelector(".btn-text");
  const btnSpinner    = submitBtn.querySelector(".btn-spinner");
  const resultCard    = document.getElementById("resultCard");
  const placeholder   = document.getElementById("resultPlaceholder");
  const resultContent = document.getElementById("resultContent");
  const resultError   = document.getElementById("resultError");
  const errorMsg      = document.getElementById("errorMsg");

  // Stats
  const statLitres    = document.getElementById("statLitres");
  const statGlasses   = document.getElementById("statGlasses");
  const statMl        = document.getElementById("statMl");
  const progressFill  = document.getElementById("progressFill");
  const progressTarget = document.getElementById("progressTarget");
  const adviceBody    = document.getElementById("adviceBody");
  const resetBtn      = document.getElementById("resetBtn");

  /* ── helpers ── */
  function setLoading(on) {
    submitBtn.disabled = on;
    btnText.hidden     = on;
    btnSpinner.hidden  = !on;
  }

  function showSection(section) {
    placeholder.hidden   = section !== "placeholder";
    resultContent.hidden = section !== "result";
    resultError.hidden   = section !== "error";
  }

  function formatLitres(l) { return l.toFixed(2); }
  function formatGlasses(l) { return Math.round(l * 4); }   // 250 ml per glass
  function formatMl(l)     { return Math.round(l * 1000); }

  function animateProgress(litres) {
    // Show progress bar filling up relative to a 4-litre max scale
    const pct = Math.min((litres / 4) * 100, 100);
    // Trigger CSS transition
    requestAnimationFrame(() => {
      progressFill.style.width = "0%";
      requestAnimationFrame(() => {
        progressFill.style.width = pct + "%";
      });
    });
  }

  /* ── validation ── */
  function validateForm() {
    const required = ["age", "gender", "weight", "activity", "climate"];
    let valid = true;
    required.forEach(id => {
      const el = document.getElementById(id);
      if (!el.value || el.value.trim() === "") {
        el.classList.add("invalid");
        valid = false;
      } else {
        el.classList.remove("invalid");
      }
    });
    return valid;
  }

  /* ── clear validation on input ── */
  ["age","gender","weight","activity","climate"].forEach(id => {
    document.getElementById(id).addEventListener("input", function () {
      this.classList.remove("invalid");
    });
  });

  /* ── form submit ── */
  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    showSection("placeholder");

    const payload = {
      name:              document.getElementById("name").value.trim() || "Friend",
      age:               document.getElementById("age").value,
      gender:            document.getElementById("gender").value,
      weight:            document.getElementById("weight").value,
      unit:              document.getElementById("unit").value,
      activity:          document.getElementById("activity").value,
      climate:           document.getElementById("climate").value,
      health_conditions: document.getElementById("health_conditions").value.trim(),
      goal:              document.getElementById("goal").value,
    };

    try {
      const resp = await fetch("/api/calculate", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });

      const data = await resp.json();

      if (!resp.ok || data.error) {
        errorMsg.textContent = data.error || "Unknown server error.";
        showSection("error");
        return;
      }

      // Populate stats
      const litres = data.baseline;
      statLitres.textContent  = formatLitres(litres) + " L";
      statGlasses.textContent = formatGlasses(litres);
      statMl.textContent      = formatMl(litres).toLocaleString();
      progressTarget.textContent = formatLitres(litres) + " L";

      animateProgress(litres);

      // Render advice text
      adviceBody.textContent = data.advice;

      showSection("result");

      // Smooth-scroll to result on mobile
      if (window.innerWidth < 769) {
        resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
      }

    } catch (err) {
      errorMsg.textContent = "Network error: " + err.message;
      showSection("error");
    } finally {
      setLoading(false);
    }
  });

  /* ── reset ── */
  resetBtn.addEventListener("click", function () {
    form.reset();
    showSection("placeholder");
    ["age","gender","weight","activity","climate"].forEach(id =>
      document.getElementById(id).classList.remove("invalid")
    );
  });

})();
