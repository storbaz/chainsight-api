const API = "https://chainsight-api.onrender.com";

chrome.alarms.create("checkWhales", { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "checkWhales") return;

  const data = await chrome.storage.sync.get(["threshold"]);
  const threshold = data.threshold || 100;

  try {
    const resp = await fetch(`${API}/v1/whales/eth?min_value=${threshold}`);
    const txs = await resp.json();

    const lastHash = await chrome.storage.local.get("lastWhaleHash");
    const seen = lastHash.lastWhaleHash || "";

    if (txs.length && txs[0].hash && txs[0].hash !== seen && !txs[0].message) {
      const tx = txs[0];
      chrome.storage.local.set({ lastWhaleHash: txs[0].hash });

      chrome.notifications.create({
        type: "basic",
        iconUrl: "icons/icon128.png",
        title: "Whale Alert",
        message: `${tx.value} ETH moved\nFrom: ${tx.from_address?.slice(0, 10)}...`,
        priority: 2,
      });
    }
  } catch (e) {}
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ topCoins: 5, threshold: 100 });
});
