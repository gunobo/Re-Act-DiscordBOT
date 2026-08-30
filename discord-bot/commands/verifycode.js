const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const { confirmVerification } = require("../lib/backendClient");

const REASON_MESSAGES = {
  no_pending: "발송된 인증 코드가 없습니다. `/인증`을 먼저 진행해주세요.",
  too_many_attempts: "시도 횟수를 초과했습니다. `/인증`을 다시 진행해주세요.",
  invalid_code: "코드가 올바르지 않습니다. 다시 확인해주세요.",
  not_whitelisted: "이메일이 화이트리스트에서 제거되었습니다. 운영진에게 문의해주세요.",
};

module.exports = {
  data: new SlashCommandBuilder()
    .setName("인증확인")
    .setDescription("이메일로 받은 인증 코드를 입력합니다")
    .addStringOption((option) =>
      option.setName("코드").setDescription("이메일로 받은 6자리 코드").setRequired(true)
    ),

  async execute(interaction) {
    await interaction.deferReply({ ephemeral: true });
    const code = interaction.options.getString("코드");

    try {
      const result = await confirmVerification(interaction.user.id, code);
      if (result.ok) {
        const embed = new EmbedBuilder()
          .setTitle("✅ 부원 인증 완료")
          .setColor(0x57f287)
          .addFields(
            { name: "이름", value: result.name, inline: true },
            { name: "학번", value: result.student_id, inline: true },
            { name: "닉네임", value: result.nickname, inline: false }
          );
        if (result.granted_role_names.length > 0) {
          embed.addFields({ name: "부여된 역할", value: result.granted_role_names.join(", ") });
        }
        await interaction.editReply({ embeds: [embed] });
      } else {
        await interaction.editReply(REASON_MESSAGES[result.reason] || "인증에 실패했습니다.");
      }
    } catch (err) {
      console.error(err);
      await interaction.editReply("서버 오류로 인증을 완료하지 못했습니다. 잠시 후 다시 시도해주세요.");
    }
  },
};
