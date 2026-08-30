const { joinCompetition } = require("../lib/backendClient");

const CUSTOM_ID_PREFIX = "join:";

function isJoinButton(customId) {
  return customId.startsWith(CUSTOM_ID_PREFIX);
}

async function handleJoinButton(interaction) {
  await interaction.deferReply({ ephemeral: true });
  const competitionCategoryId = Number(interaction.customId.slice(CUSTOM_ID_PREFIX.length));

  try {
    const result = await joinCompetition(competitionCategoryId, interaction.user.id);
    await interaction.editReply(result.message);
  } catch (err) {
    console.error(err);
    await interaction.editReply("서버 오류로 참가 신청을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.");
  }
}

module.exports = { isJoinButton, handleJoinButton };
