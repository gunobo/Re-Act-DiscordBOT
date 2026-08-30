const { SlashCommandBuilder } = require("discord.js");
const { getMyPoints } = require("../lib/backendClient");

module.exports = {
  data: new SlashCommandBuilder().setName("포인트").setDescription("내 활동 포인트를 확인합니다"),

  async execute(interaction) {
    await interaction.deferReply({ ephemeral: true });

    try {
      const result = await getMyPoints(interaction.user.id);
      if (!result.ok) {
        await interaction.editReply("부원 인증 후 이용할 수 있습니다. `/인증`을 먼저 진행해주세요.");
        return;
      }
      await interaction.editReply(`${result.name}님의 현재 포인트: **${result.total_points}P**`);
    } catch (err) {
      console.error(err);
      await interaction.editReply("서버 오류로 포인트를 조회하지 못했습니다. 잠시 후 다시 시도해주세요.");
    }
  },
};
