require("dotenv").config();
const { Client, GatewayIntentBits, Collection, Events } = require("discord.js");
const { isJoinButton, handleJoinButton } = require("./interactions/joinButton");

const client = new Client({ intents: [GatewayIntentBits.Guilds] });
client.commands = new Collection();

for (const name of ["verify", "verifycode", "points", "ranking"]) {
  const command = require(`./commands/${name}`);
  client.commands.set(command.data.name, command);
}

client.once(Events.ClientReady, (readyClient) => {
  console.log(`Logged in as ${readyClient.user.tag}`);
});

client.on(Events.InteractionCreate, async (interaction) => {
  try {
    if (interaction.isChatInputCommand()) {
      const command = client.commands.get(interaction.commandName);
      if (!command) return;
      await command.execute(interaction);
      return;
    }

    if (interaction.isButton() && isJoinButton(interaction.customId)) {
      await handleJoinButton(interaction);
      return;
    }
  } catch (err) {
    console.error(err);
    const message = "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
    if (interaction.deferred || interaction.replied) {
      await interaction.editReply(message).catch(() => {});
    } else {
      await interaction.reply({ content: message, ephemeral: true }).catch(() => {});
    }
  }
});

client.login(process.env.DISCORD_TOKEN);
