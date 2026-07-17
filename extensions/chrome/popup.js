const API = "https://chainsight-api.onrender.com";
let config = { topCoins: 5, threshold: 100, defaultChain: "ethereum" };
let portfolio = [];
let selectedChain = "ethereum";

// Load config
chrome.storage.sync.get(["topCoins", "threshold", "defaultChain", "portfolio"], (data) => {
  if (data.topCoins) config.topCoins = data.topCoins;
  if (data.threshold) config.threshold = data.threshold;
  if (data.defaultChain) config.defaultChain = data.defaultChain;
  if (data.portfolio) portfolio = data.portfolio;
  selectedChain = config.defaultChain;
  document.getElementById("topCoins").value = config.topCoins;
  document.getElementById("threshold").value = config.threshold;
  document.getElementById("defaultChain").value = config.defaultChain;
  highlightChain();
  loadAll();
});

// Tabs
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("panel-" + tab.dataset.tab).classList.add("active");
  });
});

// Chain selection
document.querySelectorAll(".chain-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    selectedChain = btn.dataset.chain;
    highlightChain();
    loadWhales();
  });
});

function highlightChain() {
  document.querySelectorAll(".chain-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.chain === selectedChain);
  });
}

// Settings
document.getElementById("settingsBtn").addEventListener("click", () => {
  document.getElementById("settingsPanel").classList.toggle("show");
});

document.getElementById("saveSettings").addEventListener("click", () => {
  config.topCoins = parseInt(document.getElementById("topCoins").value);
  config.threshold = parseInt(document.getElementById("threshold").value);
  config.defaultChain = document.getElementById("defaultChain").value;
  chrome.storage.sync.set(config);
  document.getElementById("settingsPanel").classList.remove("show");
  loadAll();
});

// Refresh
document.getElementById("refreshBtn").addEventListener("click", loadAll);

// Portfolio
document.getElementById("portAddBtn").addEventListener("click", () => {
  const id = document.getElementById("portCoin").value.trim();
  const qty = parseFloat(document.getElementById("portQty").value) || 1;
  if (!id) return;
  portfolio.push({ id, qty });
  chrome.storage.sync.set({ portfolio });
  document.getElementById("portCoin").value = "";
  loadPortfolio();
});

function removePortItem(idx) {
  portfolio.splice(idx, 1);
  chrome.storage.sync.set({ portfolio });
  loadPortfolio();
}

// Load all
async function loadAll() {
  loadFearGreed();
  loadCoins();
  loadGas();
  loadWhales();
  loadNews();
  loadPortfolio();
}

// Fear & Greed
async function loadFearGreed() {
  try {
    const r = await fetch(`${API}/v1/market/fear-greed`);
    const d = await r.json();
    const v = d.value || "--";
    let c = "#888";
    if (v < 25) c = "#ff4757";
    else if (v < 45) c = "#ff9f43";
    else if (v < 55) c = "#ffd93d";
    else if (v < 75) c = "#00d4aa";
    else c = "#00b894";
    document.getElementById("fg").innerHTML = `<div class="val" style="color:${c}">${v}</div><div class="lbl">${d.classification || ""}</div>`;
  } catch (e) {
    document.getElementById("fg").innerHTML = '<div class="val">--</div><div class="lbl">Offline</div>';
  }
}

// Coins
async function loadCoins() {
  try {
    const r = await fetch(`${API}/v1/market/top?limit=${config.topCoins}`);
    const d = await r.json();
    document.getElementById("coins").innerHTML = d.map(c => {
      const ch = c.price_change_percentage_24h || 0;
      return `<div class="coin"><div class="left"><span class="sym">${c.symbol.toUpperCase()}</span><span class="name">${c.name}</span></div><div class="right"><div class="price">$${c.current_price.toLocaleString()}</div><div class="change ${ch >= 0 ? "up" : "dn"}">${ch >= 0 ? "+" : ""}${ch.toFixed(1)}%</div></div></div>`;
    }).join("");
  } catch (e) {
    document.getElementById("coins").innerHTML = '<div class="loading">Error</div>';
  }
}

// Gas
async function loadGas() {
  try {
    const r = await fetch(`${API}/v1/whales/gas?chain=${selectedChain}`);
    const d = await r.json();
    document.getElementById("gas").innerHTML = `
      <div class="gas-item"><div class="gl">Slow</div><div class="gv">${d.low || "--"}</div></div>
      <div class="gas-item"><div class="gl">Avg</div><div class="gv">${d.average || "--"}</div></div>
      <div class="gas-item"><div class="gl">Fast</div><div class="gv">${d.fast || "--"}</div></div>`;
  } catch (e) {
    document.getElementById("gas").innerHTML = '<div class="loading">Error</div>';
  }
}

// Whales
async function loadWhales() {
  try {
    const r = await fetch(`${API}/v1/whales/chain/${selectedChain}?min_value=${config.threshold}&limit=10`);
    const d = await r.json();
    const filtered = d.filter(t => t.hash);
    if (!filtered.length) {
      document.getElementById("whales").innerHTML = '<div class="empty">No recent whale transactions</div>';
      return;
    }
    document.getElementById("whales").innerHTML = filtered.slice(0, 8).map(tx => {
      const tm = tx.timestamp ? new Date(parseInt(tx.timestamp) * 1000).toLocaleTimeString() : "";
      const chainLabel = tx.chain || selectedChain;
      const fromAddr = tx.from_address && tx.from_address.length > 20 ? tx.from_address.slice(0, 8) + "..." + tx.from_address.slice(-6) : (tx.from_address || "?");
      return `<div class="whale"><div class="wh-top"><span class="wh-val">${tx.value} ${tx.token_symbol || "ETH"}</span><span class="wh-chain">${chainLabel}</span><span class="wh-time">${tm}</span></div><div class="wh-addr">${fromAddr}</div></div>`;
    }).join("");
  } catch (e) {
    document.getElementById("whales").innerHTML = '<div class="loading">Error</div>';
  }
}

// News
async function loadNews() {
  try {
    const r = await fetch(`${API}/v1/market/news?limit=6`);
    const d = await r.json();
    if (!d.articles || !d.articles.length) {
      document.getElementById("news").innerHTML = '<div class="empty">No news available</div>';
      return;
    }
    document.getElementById("news").innerHTML = d.articles.map(a =>
      `<div class="news-item"><a href="${a.url}" target="_blank">${a.title}</a><div class="meta">${a.source} ${a.published ? "- " + a.published.split("T")[0] : ""}</div></div>`
    ).join("");
  } catch (e) {
    document.getElementById("news").innerHTML = '<div class="loading">Error</div>';
  }
}

// Portfolio
async function loadPortfolio() {
  if (!portfolio.length) {
    document.getElementById("portList").innerHTML = '<div class="empty">Add coins to track your portfolio</div>';
    document.getElementById("portTotal").innerHTML = '<div class="val">$0.00</div><div class="lbl">Total Portfolio Value</div>';
    return;
  }
  const ids = portfolio.map(p => p.id).join(",");
  try {
    const r = await fetch(`${API}/v1/market/coins?ids=${ids}`);
    const d = await r.json();
    let total = 0;
    const rows = portfolio.map((p, i) => {
      const coin = d.find(c => c.id === p.id);
      if (!coin) return "";
      const val = (coin.current_price || 0) * p.qty;
      const ch = coin.price_change_percentage_24h || 0;
      total += val;
      return `<div class="port-row"><span>${coin.symbol.toUpperCase()} ${p.qty}</span><span class="${ch >= 0 ? "up" : "dn"}">$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${ch >= 0 ? "+" : ""}${ch.toFixed(1)}%)</span><span class="dn" style="cursor:pointer;font-size:14px" onclick="window._removePort(${i})">×</span></div>`;
    }).join("");
    document.getElementById("portList").innerHTML = rows;
    document.getElementById("portTotal").innerHTML = `<div class="val">$${total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div><div class="lbl">Total Portfolio Value</div>`;
  } catch (e) {
    document.getElementById("portList").innerHTML = '<div class="loading">Error loading portfolio</div>';
  }
}

window._removePort = removePortItem;

// Auto refresh
setInterval(() => {
  const activeTab = document.querySelector(".tab.active");
  if (activeTab) {
    const tab = activeTab.dataset.tab;
    if (tab === "market") { loadFearGreed(); loadCoins(); loadGas(); }
    else if (tab === "whales") loadWhales();
    else if (tab === "portfolio") loadPortfolio();
  }
}, 60000);
