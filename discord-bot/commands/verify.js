const { SlashCommandBuilder } = require("discord.js");
const { startVerification } = require("../lib/backendClient");

const REASON_MESSAGES = {
  not_whitelisted: "등록되지 않은 학교 이메일입니다. 운영진에게 이메일 등록을 요청해주세요.",
  already_verified: "이미 부원 인증이 완료된 계정입니다.",
};

module.exports = {
  data: new SlashCommandBuilder()
    .setName("인증")
    .setDescription("학교 이메일로 부원 인증 코드를 발송합니다")
    .addStringOption((option) =>
      option.setName("이메일").setDescription("학교 이메일 주소").setRequired(true)
    ),

  async execute(interaction) {
    await interaction.deferReply({ ephemeral: true });
    const email = interaction.options.getString("이메일");

    try {
      const result = await startVerification(interaction.user.id, email);
      if (result.ok) {
        await interaction.editReply(
          `${email} 로 인증 코드를 발송했습니다.\n메일함을 확인한 뒤 \`/인증확인 코드:######\` 명령어로 코드를 입력해주세요.`
        );
      } else {
        await interaction.editReply(
          REASON_MESSAGES[result.reason] || "인증 코드 발송에 실패했습니다."
        );
      }
    } catch (err) {
      console.error(err);
      await interaction.editReply("서버 오류로 인증 코드를 발송하지 못했습니다. 잠시 후 다시 시도해주세요.");
    }
  },
};
