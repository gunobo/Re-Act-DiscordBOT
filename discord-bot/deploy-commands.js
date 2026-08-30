require("dotenv").config();
const { REST, Routes } = require("discord.js");

const commands = ["verify", "verifycode"].map((name) => require(`./commands/${name}`).data.toJSON());

const rest = new REST().setToken(process.env.DISCORD_TOKEN);

(async () => {
  try {
    await rest.put(
      Routes.applicationGuildCommands(process.env.DISCORD_CLIENT_ID, process.env.DISCORD_GUILD_ID),
      { body: commands }
    );
    console.log(`슬래시 커맨드 ${commands.length}개 등록 완료`);
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
