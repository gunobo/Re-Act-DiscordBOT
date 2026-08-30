const BACKEND_URL = process.env.BACKEND_URL;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY;

async function backendFetch(path, options = {}) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Key": INTERNAL_API_KEY,
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`backend ${path} -> ${res.status}: ${text}`);
  }

  return res.json();
}

function startVerification(discordId, email) {
  return backendFetch("/internal/verify/start", {
    method: "POST",
    body: JSON.stringify({ discord_id: discordId, email }),
  });
}

function confirmVerification(discordId, code) {
  return backendFetch("/internal/verify/confirm", {
    method: "POST",
    body: JSON.stringify({ discord_id: discordId, code }),
  });
}

function joinCompetition(competitionCategoryId, discordId) {
  return backendFetch("/internal/participation/join", {
    method: "POST",
    body: JSON.stringify({ competition_category_id: competitionCategoryId, discord_id: discordId }),
  });
}

module.exports = { startVerification, confirmVerification, joinCompetition };
