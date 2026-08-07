(function () {
  // Relative path -- works whether served from the repo root, from within
  // website/ directly, or from any static host (GitHub Pages, Vercel, ...).
  const DATA_URL = "data/all_stars_2024_2026.json";

  let allRows = [];
  const state = {
    season: "all",
    show: "all",
    search: "",
    sortKey: "all_star_selections_2024_2026",
    sortDir: "desc",
  };

  const tbody = document.getElementById("results-body");
  const emptyState = document.getElementById("empty-state");
  const summaryEl = document.getElementById("summary");
  const table = document.getElementById("results-table");

  function toBool(v) {
    return v === true || v === "True" || v === "true";
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function playerPositionLabel(row) {
    const bats = row.bats || "?";
    const throws = row.throws || "?";
    const pos = row.primary_position || "?";
    return `${pos} · ${bats}/${throws}`;
  }

  function keyStatsLabel(row) {
    if (row.stat_type === "pitching") {
      const w = row.pit_W ?? "—";
      const era = row.pit_ERA ?? "—";
      const so = row.pit_SO ?? "—";
      const whip = row.pit_WHIP ?? "—";
      return `W ${w} · ERA ${era} · SO ${so} · WHIP ${whip}`;
    }
    const hr = row.bat_HR ?? "—";
    const ops = row.bat_OPS ?? "—";
    const opsPlus = row.bat_OPS_plus ?? "—";
    return `HR ${hr} · OPS ${ops} · OPS+ ${opsPlus}`;
  }

  function brProfileUrl(row) {
    if (row.source_player_url) return row.source_player_url;
    const letter = (row.player_id || "?")[0];
    return `https://www.baseball-reference.com/players/${letter}/${row.player_id}.shtml`;
  }

  function matchesFilters(row) {
    if (state.season !== "all" && String(row.season_id) !== state.season) return false;
    if (state.show === "top100" && !toBool(row.is_show_top100)) return false;
    if (state.show === "not-top100" && toBool(row.is_show_top100)) return false;
    if (state.search) {
      const hay = `${row.full_name} ${row.team_name} ${row.team_id} ${row.player_id}`.toLowerCase();
      if (!hay.includes(state.search)) return false;
    }
    return true;
  }

  function compareRows(a, b) {
    const key = state.sortKey;
    let av = a[key];
    let bv = b[key];
    if (av === null || av === undefined) av = "";
    if (bv === null || bv === undefined) bv = "";
    const bothNumericish = av !== "" && bv !== "" && !isNaN(parseFloat(av)) && !isNaN(parseFloat(bv));
    let cmp = bothNumericish ? parseFloat(av) - parseFloat(bv) : String(av).localeCompare(String(bv));

    if (cmp === 0 && key !== "all_star_selections_2024_2026") {
      cmp = (b.all_star_selections_2024_2026 || 0) - (a.all_star_selections_2024_2026 || 0);
    }
    if (cmp === 0 && key !== "full_name") {
      cmp = String(a.full_name || "").localeCompare(String(b.full_name || ""));
    }
    if (cmp === 0 && key !== "season_id") {
      cmp = (b.season_id || 0) - (a.season_id || 0);
    }
    return state.sortDir === "asc" ? cmp : -cmp;
  }

  function detailFields(row) {
    const fields = [
      ["Player ID", row.player_id],
      ["Birth date", row.birth_date],
      ["Birth place", row.birth_place],
      ["Height", row.height_raw],
      ["Weight (lbs)", row.weight_lbs],
      ["Debut", row.debut_date],
      ["Team wins", row.team_wins],
      ["Team losses", row.team_losses],
      ["Scraped at", row.scraped_at],
    ];
    if (row.stat_type === "batting") {
      fields.push(
        ["G", row.bat_G], ["PA", row.bat_PA], ["AB", row.bat_AB], ["R", row.bat_R],
        ["H", row.bat_H], ["2B", row.bat_2B], ["3B", row.bat_3B], ["RBI", row.bat_RBI],
        ["SB", row.bat_SB], ["CS", row.bat_CS], ["BB", row.bat_BB], ["SO", row.bat_SO],
        ["BA", row.bat_BA], ["OBP", row.bat_OBP], ["SLG", row.bat_SLG]
      );
    } else {
      fields.push(
        ["L", row.pit_L], ["G", row.pit_G], ["GS", row.pit_GS], ["GF", row.pit_GF],
        ["CG", row.pit_CG], ["SHO", row.pit_SHO], ["SV", row.pit_SV], ["IP", row.pit_IP],
        ["H", row.pit_H], ["R", row.pit_R], ["ER", row.pit_ER], ["BB", row.pit_BB],
        ["HR", row.pit_HR], ["ERA+", row.pit_ERA_plus]
      );
    }
    return fields
      .map(([k, v]) => `<div><span class="k">${k}</span>${escapeHtml(v === null || v === undefined || v === "" ? "—" : String(v))}</div>`)
      .join("");
  }

  function render() {
    const filtered = allRows.filter(matchesFilters).sort(compareRows);
    tbody.innerHTML = "";
    emptyState.hidden = filtered.length > 0;

    const frag = document.createDocumentFragment();
    filtered.forEach((row) => {
      const tr = document.createElement("tr");
      tr.className = "data-row";

      const ovrCell = toBool(row.is_show_top100)
        ? `<span class="ovr">${escapeHtml(row.show_overall_rating ?? "—")}</span>` +
          `<div class="player-meta">#${escapeHtml(row.show_rank ?? "—")} · POT ${escapeHtml(row.show_potential_grade ?? "—")}</div>`
        : `<span class="ovr-empty">—</span>`;

      tr.innerHTML = `
        <td>${escapeHtml(row.all_star_selections_2024_2026 ?? "")}</td>
        <td>${escapeHtml(row.season_id ?? "")}</td>
        <td>
          <div class="player-name">${escapeHtml(row.full_name || row.player_id || "")}</div>
          <div class="player-meta">${escapeHtml(playerPositionLabel(row))}</div>
        </td>
        <td><span class="badge ${escapeHtml(row.stat_type || "")}">${escapeHtml(row.stat_type ?? "")}</span></td>
        <td>
          <div>${escapeHtml(row.team_name || "")}</div>
          <div class="player-meta">${escapeHtml(row.team_id || "")}</div>
        </td>
        <td>${escapeHtml(row.team_record || "")}</td>
        <td>${ovrCell}</td>
        <td>${escapeHtml(keyStatsLabel(row))}</td>
        <td><a class="br-link" href="${brProfileUrl(row)}" target="_blank" rel="noopener">BR &#8599;</a></td>
      `;
      tr.querySelector("a.br-link").addEventListener("click", (e) => e.stopPropagation());

      const detailTr = document.createElement("tr");
      detailTr.className = "detail-row";
      detailTr.hidden = true;
      const detailTd = document.createElement("td");
      detailTd.colSpan = 9;
      detailTd.innerHTML = `<div class="detail-grid">${detailFields(row)}</div>`;
      detailTr.appendChild(detailTd);

      tr.addEventListener("click", () => {
        detailTr.hidden = !detailTr.hidden;
      });

      frag.appendChild(tr);
      frag.appendChild(detailTr);
    });
    tbody.appendChild(frag);
  }

  function renderSummary() {
    const totalRows = allRows.length;
    const uniquePlayers = new Set(allRows.map((r) => r.player_id)).size;
    const showMatched = new Set(
      allRows.filter((r) => toBool(r.is_show_top100)).map((r) => r.player_id)
    ).size;
    const bySeason = {};
    allRows.forEach((r) => {
      bySeason[r.season_id] = (bySeason[r.season_id] || 0) + 1;
    });
    const seasonParts = Object.keys(bySeason)
      .sort()
      .map((s) => `${s}: ${bySeason[s]} rows`)
      .join(" · ");
    summaryEl.innerHTML = `
      <span><strong>${totalRows}</strong> rows</span>
      <span><strong>${uniquePlayers}</strong> unique players</span>
      <span>Show top 100: <strong>${showMatched}</strong> matched</span>
      <span>${seasonParts}</span>
    `;
  }

  function wirePillGroup(id, stateKey) {
    const group = document.getElementById(id);
    group.addEventListener("click", (e) => {
      const btn = e.target.closest(".pill");
      if (!btn) return;
      group.querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      state[stateKey] = btn.dataset.value;
      render();
    });
  }

  function wireSearch() {
    const input = document.getElementById("search-input");
    input.addEventListener("input", () => {
      state.search = input.value.trim().toLowerCase();
      render();
    });
  }

  function wireSort() {
    table.querySelectorAll("th.sortable").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.sort;
        if (state.sortKey === key) {
          state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
        } else {
          state.sortKey = key;
          state.sortDir = "desc";
        }
        table.querySelectorAll("th.sortable").forEach((h) => h.classList.remove("sorted-asc", "sorted-desc"));
        th.classList.add(state.sortDir === "asc" ? "sorted-asc" : "sorted-desc");
        render();
      });
    });
  }

  async function init() {
    wirePillGroup("season-filter", "season");
    wirePillGroup("show-filter", "show");
    wireSearch();
    wireSort();

    try {
      const res = await fetch(DATA_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      allRows = await res.json();
    } catch (err) {
      summaryEl.textContent = `Failed to load ${DATA_URL}: ${err.message}. Run "python build.py" first (writes website/data/all_stars_2024_2026.json), then "make serve".`;
      return;
    }
    renderSummary();
    render();
  }

  init();
})();
