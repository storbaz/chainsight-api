const API = "https://chainsight-api.onrender.com";

chrome.alarms.create("checkWhales", { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "checkWhales") return;

  const data = await chrome.storage.sync.get(["threshold", "defaultChain"]);
  const threshold = data.threshold || 100;
  const chain = data.defaultChain || "ethereum";

  try {
    const resp = await fetch(`${API}/v1/whales/chain/${chain}?min_value=${threshold}&limit=5`);
    const txs = await resp.json();

    const lastHash = await chrome.storage.local.get("lastWhaleHash");
    const seen = lastHash.lastWhaleHash || "";

    const valid = txs.filter(t => t.hash && !t.message);
    if (valid.length && valid[0].hash !== seen) {
      const tx = valid[0];
      chrome.storage.local.set({ lastWhaleHash: tx.hash });

      const addr = tx.from_address ? `${tx.from_address.slice(0, 8)}...` : "?";
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icons/icon128.png",
        title: `Whale Alert (${chain.toUpperCase()})`,
        message: `${tx.value} ${tx.token_symbol || chain}\nFrom: ${addr}`,
        priority: 2,
      });
    }
  } catch (e) {}
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ topCoins: 5, threshold: 100, defaultChain: "ethereum" });
});
