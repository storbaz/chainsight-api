const API = "https://chainsight-api.onrender.com";

let config = { topCoins: 5, threshold: 100 };

chrome.storage.sync.get(["topCoins", "threshold"], (data) => {
  if (data.topCoins) config.topCoins = data.topCoins;
  if (data.threshold) config.threshold = data.threshold;
  document.getElementById("topCoins").value = config.topCoins;
  document.getElementById("threshold").value = config.threshold;
  loadAll();
});

document.getElementById("settingsBtn").onclick = () => {
  document.getElementById("settingsPanel").classList.toggle("show");
};

document.getElementById("saveSettings").onclick = () => {
  config.topCoins = parseInt(document.getElementById("topCoins").value);
  config.threshold = parseInt(document.getElementById("threshold").value);
  chrome.storage.sync.set(config);
  document.getElementById("settingsPanel").classList.remove("show");
  loadAll();
};

async function loadAll() {
  loadFearGreed();
  loadCoins();
  loadGas();
  loadWhales();
}

async function loadFearGreed() {
  try {
    const resp = await fetch(`${API}/v1/market/fear-greed`);
    const data = await resp.json();
    const val = data.value || "--";
    const cls = data.classification || "Loading...";
    let color = "#888";
    if (val < 25) color = "#ff4757";
    else if (val < 45) color = "#ff9f43";
    else if (val < 55) color = "#ffd93d";
    else if (val < 75) color = "#00d4aa";
    else color = "#00b894";
    document.getElementById("fg").innerHTML = `<div class="val" style="color:${color}">${val}</div><div class="lbl">${cls}</div>`;
  } catch (e) {
    document.getElementById("fg").innerHTML = '<div class="val">--</div><div class="lbl">Offline</div>';
  }
}

async function loadCoins() {
  try {
    const resp = await fetch(`${API}/v1/market/top?limit=${config.topCoins}`);
    const data = await resp.json();
    document.getElementById("coins").innerHTML = data.map(c => {
      const ch = c.price_change_percentage_24h || 0;
      return `<div class="coin">
        <div class="left"><span class="sym">${c.symbol.toUpperCase()}</span><span class="name">${c.name}</span></div>
        <div class="right"><div class="price">$${c.current_price.toLocaleString()}</div><div class="change ${ch >= 0 ? "up" : "dn"}">${ch >= 0 ? "+" : ""}${ch.toFixed(1)}%</div></div>
      </div>`;
    }).join("");
  } catch (e) {
    document.getElementById("coins").innerHTML = '<div class="loading">Error loading prices</div>';
  }
}

async function loadGas() {
  try {
    const resp = await fetch(`${API}/v1/whales/gas`);
    const data = await resp.json();
    document.getElementById("gas").innerHTML = `
      <div class="gas-item"><div class="gl">Slow</div><div class="gv">${data.low || "--"}</div></div>
      <div class="gas-item"><div class="gl">Avg</div><div class="gv">${data.average || "--"}</div></div>
      <div class="gas-item"><div class="gl">Fast</div><div class="gv">${data.fast || "--"}</div></div>
    `;
  } catch (e) {
    document.getElementById("gas").innerHTML = '<div class="loading">Error</div>';
  }
}

async function loadWhales() {
  try {
    const resp = await fetch(`${API}/v1/whales/eth?min_value=${config.threshold}`);
    const data = await resp.json();
    if (!data.length || data[0].message || data[0].error) {
      document.getElementById("whales").innerHTML = '<div class="loading">No recent whales</div>';
      return;
    }
    document.getElementById("whales").innerHTML = data.slice(0, 5).map(tx => {
      const time = tx.timestamp ? new Date(parseInt(tx.timestamp) * 1000).toLocaleTimeString() : "";
      return `<div class="whale">
        <div class="wh-top"><span class="wh-val">${tx.value} ETH</span><span class="wh-time">${time}</span></div>
        <div class="wh-addr">From: ${tx.from_address || "?"}</div>
      </div>`;
    }).join("");
  } catch (e) {
    document.getElementById("whales").innerHTML = '<div class="loading">Error loading whales</div>';
  }
}

setInterval(loadAll, 60000);
