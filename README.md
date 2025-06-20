# CF-Shield

CF-Shield is a Python script for detecting DDoS attacks and enabling security measures on Cloudflare automatically.

## Installation

### Way 1: Using pip

```bash
pip install cf-shield
```

Then to run the script, you can use the following command:

```bash
cf-shield
```
or if it is not in your PATH, you can use the following command:

```bash
python3 -m cf-shield
```

If this fails, you can try using git.


### Way 2: Using git

First, you will need to get your Cloudflare email, API token, zone ID, and account ID.

```bash
git clone https://github.com/Sakura-sx/cf-shield.git
cd cf-shield
python3 main.py
```
When running the script for the first time, it will ask you for your Cloudflare email, API token, zone ID, and account ID. More info on [Setup](#setup).

The dependencies should be installed automatically. If not, you can install them manually by running `python3 -m pip install -r requirements.txt`.

## Setup
To setup the script, you will need to run the script and follow the prompts. First run the commands on [Installation](#installation). Here you have a list of what the script will ask you for and what you need to do. The prompts with `default:` are optional and will be set to the default value if you don't enter anything.

The full setup looks like this:

```
  /$$$$$$  /$$$$$$$$       /$$$$$$  /$$       /$$           /$$       /$$
 /$$__  $$| $$_____/      /$$__  $$| $$      |__/          | $$      | $$
| $$  \__/| $$           | $$  \__/| $$$$$$$  /$$  /$$$$$$ | $$  /$$$$$$$
| $$      | $$$$$ /$$$$$$|  $$$$$$ | $$__  $$| $$ /$$__  $$| $$ /$$__  $$
| $$      | $$__/|______/ \____  $$| $$  \ $$| $$| $$$$$$$$| $$| $$  | $$
| $$    $$| $$            /$$  \ $$| $$  | $$| $$| $$_____/| $$| $$  | $$
|  $$$$$$/| $$           |  $$$$$$/| $$  | $$| $$|  $$$$$$$| $$|  $$$$$$$
 \______/ |__/            \______/ |__/  |__/|__/ \_______/|__/ \_______/




Welcome to CF-Shield, we will now set it up for you.
What's the domain(s) you want to use? (e.g. "example.com,www.example.com" or "example.com")
example.com
What's the email you used to sign up for Cloudflare? (e.g. example@example.com)
example@example.com
Please create an API token and copy it here (e.g. aK-MaF3oyTrPDD8YoNBlvqo0ous7BOeSA7te84OR)
aK-MaF3oyTrPDD8YoNBlvqo0ous7BOeSA7te84OR
Please copy the zone ID from the URL of your Cloudflare dashboard (e.g. 1b7c0e3d41f09ceb9cbcde6b0c7bc819)
1b7c0e3d41f09ceb9cbcde6b0c7bc819
Please copy the account ID from the URL of your Cloudflare dashboard (e.g. 6dead821d9eb4c42f8a8dda399651660)
6dead821d9eb4c42f8a8dda399651660
Please enter the CPU usage threshold in percentage (default: 80)
80
What's the challenge type you want to use? (default: managed_challenge, options: managed_challenge, js_challenge, challenge)
managed_challenge
If you want to use a Discord webhook, please enter the webhook URL (default: None)
https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz
If you want to use a Telegram bot, please enter the bot token (default: None)
1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ
Please enter the chat ID for the telegram bot (default: None)
1234567890
How many seconds do you want to wait before disabling the challenge rule? (default: auto eg. 30)
30
Setup successful!
  Ruleset ID: abacebd975b04e398fe02ba19614aa8b
  Rule ID: e65dd32a32874c0aa3339af385ca95db
Saving configuration to .env file...
Configuration saved successfully!
Setup complete! Starting monitoring...
```

### 1. Domains
`What's the domain(s) you want to use? (e.g. "example.com,www.example.com" or "example.com" or "all")`

This is the domain(s) you want to use. You can add multiple domains by separating them with a comma. The domains must be on the same [Zone](https://developers.cloudflare.com/fundamentals/concepts/accounts-and-zones/#zones) (meaning a single WAF rule can be applied to all of them).

If you want to use all domains in the zone, you can enter `all`.

If you change this after the inital setup, you will need to remove the rule from the dashboard and run the script again.

### 2. Email
`What's the email you used to sign up for Cloudflare? (e.g. example@example.com)`

This must be the email you used to sign up for Cloudflare. You can find it [here](https://dash.cloudflare.com/profile).

### 3. API Token
`Please create an API token and copy it here (e.g. aK-MaF3oyTrPDD8YoNBlvqo0ous7BOeSA7te84OR)`

This is the API token you need to create. You can create it [here](https://dash.cloudflare.com/profile/api-tokens). There is a guide [here](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/). You need to create a token with `Zone WAF Write` permissions. It should be 40 characters long and only contain letters, numbers and dashes.

### 4. Zone ID
`Please copy the zone ID from the URL of your Cloudflare dashboard (e.g. 1b7c0e3d41f09ceb9cbcde6b0c7bc819)`

This is the zone ID you need to copy from the URL of your Cloudflare dashboard. You can find it [here](https://developers.cloudflare.com/fundamentals/account/find-account-and-zone-ids/#copy-your-zone-id). It should be 32 characters long and only contain letters and numbers.

### 5. Account ID
`Please copy the account ID from the URL of your Cloudflare dashboard (e.g. 6dead821d9eb4c42f8a8dda399651660)`

The account ID can be found below the zone ID. It should not be the same as the zone ID. If you can't find it, there is more info [here](https://developers.cloudflare.com/fundamentals/account/find-account-and-zone-ids/#copy-your-account-id). It should be 32 characters long and only contain letters and numbers.

#### This was the last prompt you could not set blank. After setting this you can leave blank the other prompts.

### 6. CPU Threshold
`Please enter the CPU usage threshold in percentage (default: 80)`

This is the CPU usage threshold you want to use. The script will enable the challenge rule if the CPU usage is greater than this threshold. It should be a number between 0 and 100. It is advised to set it to a value between 50 and 90 depending on your server's performance and average load.

### 7. Challenge Type
`What's the challenge type you want to use? (default: managed_challenge, options: managed_challenge, js_challenge, challenge)`

This is the challenge type you want to use. You can choose between `managed_challenge`, `js_challenge` and `challenge`.

`js_challenge` is a challenge that uses JavaScript to detect bots. It is the fastest challenge type to load, but it is also not as effective as `challenge` or `managed_challenge`.

`challenge` is a challenge that uses a CAPTCHA to detect bots, it was the first challenge type to be released by Cloudflare. It is the most effective challenge type, but it is also the most resource intensive and slowest to load.

`managed_challenge` is the default challenge type. Cloudflare will choose to use `js_challenge` or `challenge` based on how likely it thinks the request is a bot.

Usually it is best to start with `managed_challenge` and then switch to `challenge` if the bots are still able to bypass the challenge.

If you change this after the inital setup, you will need to remove the rule from the dashboard and run the script again.

### 8. Discord Webhook (optional)
`If you want to use a Discord webhook, please enter the webhook URL (default: None)`

This is the Discord webhook URL you want to use. You can find a guide [here](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks). It should be a valid Discord webhook URL. You will get messages when the challenge is enabled or disabled.

If you don't want to use a Discord webhook, you can leave it blank.

### 9. Telegram Bot Token (optional)
`If you want to use a Telegram bot, please enter the bot token (default: None)`

This is the Telegram bot token you want to use. You can find a guide [here](https://core.telegram.org/bots/tutorial#obtain-your-bot-token). It should be a valid Telegram bot token. You will get messages when the challenge is enabled or disabled. If you set a bot token, you will also need to set a chat ID.

If you don't want to get Telegram notifications, you can leave it blank.

### 9.1. Telegram Chat ID (optional, only if you set a Telegram bot token)
`Please enter the chat ID for the telegram bot (default: None)`

This is the chat ID you want to use. You can find a guide [here](https://core.telegram.org/bots/tutorial#obtain-your-chat-id). It should be a valid Telegram chat ID. You will get messages when the challenge is enabled or disabled. If you set a bot token, you will also need to set a chat ID.

If you haven't set a bot token, you will not see this prompt.

### 10. Challenge Rule Disable Delay
`How many seconds do you want to wait before disabling the challenge rule? (default: auto eg. 30)`

This is the delay in seconds you want to use before disabling the challenge rule. This is to avoid the rule to be disabled and enabled fast when the CPU lowers because of the challenge. It should be a number between 0 and infinity. But it is advised to set it to a value between 5 and 1800. You can also set it to "auto" and the script will choose the value dynamically.


## Usage
```bash
cf-shield
```
or if it is not in your PATH, you can use the following command:
```bash
python3 -m cf-shield
```

Or if it doesn't work, you can install it using git. (See [Installation](#installation)) and then run the following command:

```bash
python3 main.py
```
To modify the config after the inital setup, you can edit the .env file or use the `setup` argument like this (See [Setup](#setup)):

```bash
python3 main.py setup
```




## Roadmap
- [x] Adding a way to add multiple domains.
- [x] Making the challenge type customizable instead of `managed_challenge`.
- [x] Discord webhook notifications.
- [x] Adding a configurable delay before disabling the challenge rule.
- [x] Telegram notifications.
- [x] Full guide in the README.md.
- [x] A way to use all domains in the zone.
- [x] Slack notifications.
- [x] Set disable delay automatically.
- [x] Averaged CPU monitoring option.
- [ ] Automated CPU spike detection option.
- [ ] Add ratelimit challenge.


## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

## License

[GPL-3.0](https://choosealicense.com/licenses/gpl-3.0/)