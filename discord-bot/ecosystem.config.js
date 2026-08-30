module.exports = {
  apps: [
    {
      name: "react-bot",
      script: "index.js",
      cwd: __dirname,
      env: {
        NODE_ENV: "production",
      },
    },
  ],
};
