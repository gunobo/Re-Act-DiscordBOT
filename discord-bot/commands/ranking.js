const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const { getLeaderboard } = require("../lib/backendClient");

const MEDALS = ["🥇", "🥈", "🥉"];

module.exports = {
  data: new SlashCommandBuilder().setName("랭킹").setDescription("활동 포인트 랭킹을 확인합니다"),

  async execute(interaction) {
    await interaction.deferReply();

    try {
      const result = await getLeaderboard(10);
      if (result.entries.length === 0) {
        await interaction.editReply("아직 랭킹에 표시할 부원이 없습니다.");
        return;
      }

      const lines = result.entries.map((entry, index) => {
        const medal = MEDALS[index] || `${index + 1}.`;
        return `${medal} ${entry.name} (${entry.student_id}) - ${entry.total_points}P`;
      });

      const embed = new EmbedBuilder()
        .setTitle("🏆 RE-ACT 활동 포인트 랭킹")
        .setColor(0x5865f2)
        .setDescription(lines.join("\n"));

      await interaction.editReply({ embeds: [embed] });
    } catch (err) {
      console.error(err);
      await interaction.editReply("서버 오류로 랭킹을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.");
    }
  },
};
