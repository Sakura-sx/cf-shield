import os
import re
try:
    import requests
    import psutil
    from cloudflare import Cloudflare
    from dotenv import load_dotenv
    from discord_webhook import DiscordWebhook
    import time
    import logging
    import colorlog
    from colorlog import ColoredFormatter
except ImportError:
    print("installing dependencies...")
    os.system("python3 -m pip install -r requirements.txt")

def setup():
    print("What's the domain(s) you want to use? (e.g. \"example.com,www.example.com\" or \"example.com\" or \"all\")")
    domains = input().split(",")
    if not domains:
        logging.error("No domains provided, please provide a domain")
        return
    else:
        if domains[0] != "all":
            for domain in domains:
                if not re.match(r"^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$", domain.strip()):
                    logging.error(f"Invalid domain: {domain}")
                    return
        else:
            domains = ["all"]
    print("What's the email you used to sign up for Cloudflare? (e.g. example@example.com)")
    email = input()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email.strip()):
        logging.error(f"Invalid email: {email}")
        return
    print("Please create an API token and copy it here (e.g. aK-MaF3oyTrPDD8YoNBlvqo0ous7BOeSA7te84OR)")
    api_token = input()
    if not re.match(r"^[a-zA-Z0-9-]{40}$", api_token.strip()):
        logging.error(f"Invalid API token: {api_token}")
        return
    print("Please copy the zone ID from the URL of your Cloudflare dashboard (e.g. 1b7c0e3d41f09ceb9cbcde6b0c7bc819)")
    zone_id = input()
    if not re.match(r"^[a-zA-Z0-9]{32}$", zone_id.strip()):
        logging.error(f"Invalid zone ID: {zone_id}")
        return
    print("Please copy the account ID from the URL of your Cloudflare dashboard (e.g. 6dead821d9eb4c42f8a8dda399651660)")
    account_id = input()
    if not re.match(r"^[a-zA-Z0-9]{32}$", account_id.strip()):
        logging.error(f"Invalid account ID: {account_id}")
        return
    elif zone_id == account_id:
        logging.error("Zone ID and account ID are the same, that means you pasted one of them in the wrong place")
        return
    print("Please enter the CPU usage threshold in percentage (default: 80)")
    cpu_threshold = input()
    if not cpu_threshold:
        cpu_threshold = 80
    elif not re.match(r"^[0-9]+$", cpu_threshold.strip()):
        logging.error(f"Invalid CPU threshold: {cpu_threshold}")
        return
    elif int(cpu_threshold) > 100:
        logging.error("CPU threshold cannot be greater than 100")
        return
    elif int(cpu_threshold) < 10:
        logging.error("You have set the CPU threshold to a very low value, if you know what you are doing, you can ignore this message")
    elif int(cpu_threshold) <= 0:
        logging.error("CPU threshold cannot be less than or equal to 0")
        return
    print("What's the challenge type you want to use? (default: managed_challenge, options: managed_challenge, js_challenge, challenge)")
    challenge_type = input()
    if not challenge_type:
        challenge_type = "managed_challenge"
    elif challenge_type not in ["managed_challenge", "js_challenge", "challenge"]:
        logging.error("Invalid challenge type, please enter a valid challenge type")
        return
    print("If you want to use a Discord webhook, please enter the webhook URL (default: None)")
    discord_webhook = input()
    if not discord_webhook:
        discord_webhook = None
    else:
        if not re.match(r"^https://(discord\.com|ptb\.discord\.com|canary\.discord\.com)/api/webhooks/[0-9]+/[a-zA-Z0-9-]+$", discord_webhook.strip()):
            logging.error("Invalid Discord webhook URL, please enter a valid Discord webhook URL")
            return
        else:
            logging.info("Sending a test message to the Discord webhook...")
            try:
                webhook = DiscordWebhook(url=discord_webhook, content="Test message from CF-Shield")
                webhook.execute()
                logging.info("Test message sent successfully!")
            except Exception as e:
                logging.error(f"Error sending test message to Discord webhook: {e}")
                return
    print("If you want to use a Telegram bot, please enter the bot token (default: None)")
    telegram_bot_token = input()
    if not telegram_bot_token:
        telegram_bot_token = None
    else:
        if not re.match(r"([0-9]{8,10}):[A-za-z0-9]{35}", telegram_bot_token.strip()):
            logging.error("Invalid Telegram bot token, please enter a valid Telegram bot token")
            return
        print("Please enter the chat ID for the telegram bot")
        telegram_chat_id = input()
        if not re.match(r"^[0-9]+$", telegram_chat_id.strip()):
            logging.error("Invalid Telegram chat ID, please enter a valid Telegram chat ID")
            return
        else:
            logging.info("Sending a test message to the Telegram bot...")
            try:
                send_telegram_message("Test message from CF-Shield", telegram_chat_id, telegram_bot_token)
                logging.info("Test message sent successfully!")
            except Exception as e:
                logging.error(f"Error sending test message to Telegram bot: {e}")
    print("How many seconds do you want to wait before disabling the challenge rule? (default: 30)")
    disable_delay = input()
    if not disable_delay:
        disable_delay = 30
    elif not re.match(r"^[0-9]+$", disable_delay.strip()):
        logging.error("Invalid disable delay, please enter a valid disable delay")
        return
    elif disable_delay < 0:
        logging.error("Disable delay cannot be less than 0")
        return
    elif disable_delay < 5:
        logging.warning("You have set the disable delay to a very low value, if you know what you are doing, you can ignore this message")
    elif disable_delay > 1800:
        logging.warning("You have set the disable delay to a very high value, if you know what you are doing, you can ignore this message")

    cf = Cloudflare(api_token=api_token)
    
    try:
        rulesets_page = cf.rulesets.list(zone_id=zone_id)
        
        target_ruleset_id = None
        for ruleset in rulesets_page.result:
            if ruleset.phase == "http_request_firewall_custom":
                target_ruleset_id = ruleset.id
                break
        
        if not target_ruleset_id:
            logging.info("No http_request_firewall_custom ruleset found.")
            
            custom_ruleset = cf.rulesets.create(
                kind="zone",
                name="cf-shield-challenge",
                phase="http_request_firewall_custom",
                zone_id=zone_id
            )
            target_ruleset_id = custom_ruleset.id
        
        existing_ruleset = cf.rulesets.get(zone_id=zone_id, ruleset_id=target_ruleset_id)
        
        cf_shield_rule_id = None
        try:
            for rule in existing_ruleset.rules:
                if rule.description and "CF-Shield" in rule.description:
                    cf_shield_rule_id = rule.id
                    break
        except Exception as e:
            logging.error(f"Error checking for existing CF-Shield rule: {e}")
            cf_shield_rule_id = None
        
        if not cf_shield_rule_id:
            expression = "("
            if domains[0] != "all":
                for domain in domains:
                    expression += f"http.host eq \"{domain}\" or "
                expression = expression[:-4] + ")"
            else:
                expression = "(http.host ne \"example.invalid\")"
            new_rule = cf.rulesets.rules.create(
                ruleset_id=target_ruleset_id,
                zone_id=zone_id,
                action=challenge_type,
                expression=expression,
                description="CF-Shield",
                enabled=False
            )
            cf_shield_rule_id = new_rule.id

        print(f"Setup successful!")
        print(f"  Ruleset ID: {target_ruleset_id}")
        print(f"  Rule ID: {cf_shield_rule_id}")
        
    except Exception as e:
        logging.error(f"Error working with rulesets: {e}")
        logging.error("Note: You may need to adjust your API token permissions.")
        return

    print("Saving configuration to .env file...")
    try:
        with open(".env", "w") as f:
            f.write(f"CF_EMAIL={email}\n")
            f.write(f"CF_API_TOKEN={api_token}\n")
            f.write(f"CF_ZONE_ID={zone_id}\n")
            f.write(f"CF_ACCOUNT_ID={account_id}\n")
            f.write(f"CF_RULESET_ID={target_ruleset_id}\n")
            f.write(f"CF_RULE_ID={cf_shield_rule_id}\n")
            f.write(f"DOMAINS={','.join(domains)}\n")
            f.write(f"CPU_THRESHOLD={cpu_threshold}\n")
            f.write(f"CHALLENGE_TYPE={challenge_type}\n")
            f.write(f"DISCORD_WEBHOOK={discord_webhook}\n")
            f.write(f"TELEGRAM_BOT_TOKEN={telegram_bot_token}\n")
            f.write(f"TELEGRAM_CHAT_ID={telegram_chat_id}\n")
            f.write(f"DISABLE_DELAY={disable_delay}\n")
            f.write(f"SETUP=true\n")
        print("Configuration saved successfully!")
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        return
        
    print("Setup complete! Starting monitoring...")
    main()

def send_telegram_message(message, chat_id, bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(url, json=data)

def main():
    
    cf = Cloudflare(api_token=os.getenv("CF_API_TOKEN"))
    zone_id = os.getenv("CF_ZONE_ID")
    account_id = os.getenv("CF_ACCOUNT_ID")
    ruleset_id = os.getenv("CF_RULESET_ID")
    rule_id = os.getenv("CF_RULE_ID")
    domains = os.getenv("DOMAINS").split(",") if "," in os.getenv("DOMAINS") else [os.getenv("DOMAINS")]
    cpu_threshold = float(os.getenv("CPU_THRESHOLD", "80"))
    challenge_type = os.getenv("CHALLENGE_TYPE", "managed_challenge")
    discord_webhook = os.getenv("DISCORD_WEBHOOK", None)
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", None)
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", None)
    disable_delay = int(os.getenv("DISABLE_DELAY", 30))
    
    if not all([zone_id, ruleset_id, rule_id]):
        logging.error("Missing configuration. Please run setup again.")
        logging.error(f"Zone ID: {zone_id}")
        logging.error(f"Ruleset ID: {ruleset_id}")
        logging.error(f"Rule ID: {rule_id}")
        return
    
    logging.info(f"Monitoring CPU usage for domains: {', '.join(domains)}")
    logging.info(f"CPU threshold: {cpu_threshold}%")
    
    rule_enabled = False
    t = 1
    while True:
        time.sleep(1)
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            logging.info(f"Current CPU usage: {cpu_usage}%")

            if cpu_usage > cpu_threshold:
                t = 0
            else:
                t += 1
            
            if t == 0 and not rule_enabled:
                logging.info(f"CPU usage ({cpu_usage}%) exceeds threshold ({cpu_threshold}%)")
                cf.rulesets.rules.edit(
                    rule_id=rule_id,
                    ruleset_id=ruleset_id,
                    zone_id=zone_id,
                    enabled=True
                )
                rule_enabled = True
                logging.info("Challenge rule enabled!")

                if discord_webhook:
                    webhook = DiscordWebhook(url=discord_webhook, content=f"The CPU usage is too high, enabling challenge rule for {', '.join(domains)}...")
                    webhook.execute()
                if telegram_bot_token:
                    send_telegram_message(f"The CPU usage is too high, enabling challenge rule for {', '.join(domains)}...", telegram_chat_id, telegram_bot_token)
                
            elif t > disable_delay and rule_enabled:
                logging.info("CPU usage returned to normal, disabling challenge rule...")
                cf.rulesets.rules.edit(
                    rule_id=rule_id,
                    ruleset_id=ruleset_id,
                    zone_id=zone_id,
                    enabled=False
                )
                rule_enabled = False
                logging.info("Challenge rule disabled!")
                if discord_webhook:
                    webhook = DiscordWebhook(url=discord_webhook, content=f"The CPU usage is back to normal, disabling challenge rule for {', '.join(domains)}...")
                    webhook.execute()
                if telegram_bot_token:
                    send_telegram_message(f"The CPU usage is back to normal, disabling challenge rule for {', '.join(domains)}...", telegram_chat_id, telegram_bot_token)
                
        except KeyboardInterrupt:
            logging.info("\nMonitoring stopped by user")
            break
        except Exception as e:
            logging.error(f"Error during monitoring: {e}")
            break


def run():
    print(r"""
  /$$$$$$  /$$$$$$$$       /$$$$$$  /$$       /$$           /$$       /$$
 /$$__  $$| $$_____/      /$$__  $$| $$      |__/          | $$      | $$
| $$  \__/| $$           | $$  \__/| $$$$$$$  /$$  /$$$$$$ | $$  /$$$$$$$
| $$      | $$$$$ /$$$$$$|  $$$$$$ | $$__  $$| $$ /$$__  $$| $$ /$$__  $$
| $$      | $$__/|______/ \____  $$| $$  \ $$| $$| $$$$$$$$| $$| $$  | $$
| $$    $$| $$            /$$  \ $$| $$  | $$| $$| $$_____/| $$| $$  | $$
|  $$$$$$/| $$           |  $$$$$$/| $$  | $$| $$|  $$$$$$$| $$|  $$$$$$$
 \______/ |__/            \______/ |__/  |__/|__/ \_______/|__/ \_______/
                                                                         
                                                                         
                                                                         
""")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    try:
        load_dotenv()
        if os.getenv("SETUP") == "true":
            logging.info("Configuration found, starting monitoring...")
            main()
        else:
            raise Exception("Setup not completed")
    except Exception:
        print(f"Welcome to CF-Shield, we will now set it up for you.")
        setup()


if __name__ == "__main__":
    run()