import os
import re
import sys
import requests
import psutil
from cloudflare import Cloudflare
from dotenv import load_dotenv
from discord_webhook import DiscordWebhook
import time
import logging
import colorlog
from colorlog import ColoredFormatter
from slack_sdk.webhook import WebhookClient

def setup():
    print("What's the domain(s) you want to use? (default: all, e.g. \"example.com,www.example.com\" or \"example.com\")")
    domains = input().strip().split(",")
    if not domains:
        domains = ["all"]
    else:
        if domains[0] != "all":
            for domain in domains:
                if domain.strip() == "":
                    logging.error("No domain provided, please provide a domain")
                    return
                elif not re.match(r"^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$", domain.strip()):
                    logging.error(f"Invalid domain: {domain}")
                    return
        else:
            domains = ["all"]

    logging.debug(f"Domains: {domains}")


    print("What's the email you used to sign up for Cloudflare? (e.g. example@example.com)")
    email = input().strip()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        logging.error(f"Invalid email: {email}")
        return
    logging.debug(f"Email: {email}")


    print("Please create an API token and copy it here (e.g. aK-MaF3oyTrPDD8YoNBlvqo0ous7BOeSA7te84OR)")
    api_token = input().strip()
    if not re.match(r"^[a-zA-Z0-9-]{40}$", api_token):
        logging.error(f"Invalid API token: {api_token}")
        return
    logging.debug(f"API token: {api_token}")


    print("Please copy the zone ID from the URL of your Cloudflare dashboard (e.g. 1b7c0e3d41f09ceb9cbcde6b0c7bc819)")
    zone_id = input().strip()
    if not re.match(r"^[a-zA-Z0-9]{32}$", zone_id):
        logging.error(f"Invalid zone ID: {zone_id}")
        return
    logging.debug(f"Zone ID: {zone_id}")

    
    print("Please copy the account ID from the URL of your Cloudflare dashboard (e.g. 6dead821d9eb4c42f8a8dda399651660)")
    account_id = input().strip()
    if not re.match(r"^[a-zA-Z0-9]{32}$", account_id):
        logging.error(f"Invalid account ID: {account_id}")
        return
    elif zone_id == account_id:
        logging.error("Zone ID and account ID are the same, that means you pasted one of them in the wrong place")
        return
    logging.debug(f"Account ID: {account_id}")


    print("Please enter the CPU usage threshold in percentage (default: 80)")
    cpu_threshold = input().strip()
    if not cpu_threshold:
        cpu_threshold = 80
    elif not re.match(r"^[0-9]+$", cpu_threshold):
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
    challenge_type = input().strip()
    if not challenge_type:
        challenge_type = "managed_challenge"
    elif challenge_type not in ["managed_challenge", "js_challenge", "challenge"]:
        logging.error("Invalid challenge type, please enter a valid challenge type")
        return
    logging.debug(f"Challenge type: {challenge_type}")

    
    print("If you want to use a Slack webhook, please enter the webhook URL (default: None)")
    slack_webhook = input().strip()
    if not slack_webhook:
        slack_webhook = None
    else:
        if not re.match(r"^https:\/\/hooks\.slack\.com\/services\/[A-Za-z0-9\/]+$", slack_webhook):
            logging.error("Invalid Slack webhook URL, please enter a valid Slack webhook URL")
            return
        else:
            logging.info("Sending a test message to the Slack webhook...")
            try:
                webhook = WebhookClient(slack_webhook)
                webhook.send(text="Test message from CF-Shield")
                logging.info("Test message sent successfully!")
            except Exception as e:
                logging.error(f"Error sending test message to Slack webhook: {e}")
                return
            else:
                print("If you want to use a custom message for the attack start, please enter the message (default: The CPU usage is too high, enabling challenge rule for {', '.join(domains)}...)")
                slack_custom_message = input().strip()
                if not slack_custom_message:
                    slack_custom_message = f"The CPU usage is too high, enabling challenge rule for {', '.join(domains)}..."

                print(f"If you want to use a custom message for the attack end, please enter the message (default: The CPU usage is back to normal, disabling challenge rule for {', '.join(domains)}...)")
                slack_custom_message_end = input().strip()
                if not slack_custom_message_end:
                    slack_custom_message_end = f"The CPU usage is back to normal, disabling challenge rule for {', '.join(domains)}..."

                print("If you want to use a custom message for when the CPU usage is too high 10 seconds after the attack started, please enter the message (default: The CPU usage is still too high, disabling challenge rule for {', '.join(domains)}...)")
                slack_custom_message_10_seconds = input().strip()
                if not slack_custom_message_10_seconds:
                    slack_custom_message_10_seconds = f"The CPU usage is still too high, the challenge rule might not be working..."

    logging.debug(f"Slack webhook: {slack_webhook}")
    logging.debug(f"Slack custom message: {slack_custom_message}")
    logging.debug(f"Slack custom message end: {slack_custom_message_end}")
    logging.debug(f"Slack custom message 10 seconds: {slack_custom_message_10_seconds}")


    print("If you want to use a Discord webhook, please enter the webhook URL (default: None)")
    discord_webhook = input().strip()
    if not discord_webhook:
        discord_webhook = None
    else:
        if not re.match(r"^https:\/\/(discord\.com|ptb\.discord\.com|canary\.discord\.com)\/api\/webhooks\/[0-9]+\/[a-zA-Z0-9-]+$", discord_webhook):
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
            else:
                print(f"If you want to use a custom message for the attack start, please enter the message (default: The CPU usage is too high, enabling challenge rule for {', '.join(domains)}...)")
                discord_custom_message = input().strip()
                if not discord_custom_message:
                    discord_custom_message = f"The CPU usage is too high, enabling challenge rule for {', '.join(domains)}..."

                print(f"If you want to use a custom message for the attack end, please enter the message (default: The CPU usage is back to normal, disabling challenge rule for {', '.join(domains)}...)")
                discord_custom_message_end = input().strip()
                if not discord_custom_message_end:
                    discord_custom_message_end = f"The CPU usage is back to normal, disabling challenge rule for {', '.join(domains)}..."

                print("If you want to use a custom message for when the CPU usage is too high 10 seconds after the attack started, please enter the message (default: The CPU usage is still too high, the challenge rule might not be working...)")
                discord_custom_message_10_seconds = input().strip()
                if not discord_custom_message_10_seconds:
                    discord_custom_message_10_seconds = f"The CPU usage is still too high, the challenge rule might not be working..."

    logging.debug(f"Discord webhook: {discord_webhook}")
    logging.debug(f"Discord custom message: {discord_custom_message}")
    logging.debug(f"Discord custom message end: {discord_custom_message_end}")
    logging.debug(f"Discord custom message 10 seconds: {discord_custom_message_10_seconds}")
    

    print("If you want to use a Telegram bot, please enter the bot token (default: None)")
    telegram_bot_token = input().strip()
    if not telegram_bot_token:
        telegram_bot_token = None
    else:
        if not re.match(r"([0-9]{8,10}):[A-za-z0-9]{35}", telegram_bot_token):
            logging.error("Invalid Telegram bot token, please enter a valid Telegram bot token")
            return
        print("Please enter the chat ID for the telegram bot")
        telegram_chat_id = input().strip()
        if not re.match(r"^[0-9]+$", telegram_chat_id):
            logging.error("Invalid Telegram chat ID, please enter a valid Telegram chat ID")
            return
        else:
            logging.info("Sending a test message to the Telegram bot...")
            try:
                send_telegram_message("Test message from CF-Shield", telegram_chat_id, telegram_bot_token)
                logging.info("Test message sent successfully!")
            except Exception as e:
                logging.error(f"Error sending test message to Telegram bot: {e}")
            else:
                print(f"If you want to use a custom message for the attack start, please enter the message (default: The CPU usage is too high, enabling challenge rule for {', '.join(domains)}...)")
                telegram_custom_message = input().strip()
                if not telegram_custom_message:
                    telegram_custom_message = f"The CPU usage is too high, enabling challenge rule for {', '.join(domains)}..."

                print(f"If you want to use a custom message for the attack end, please enter the message (default: The CPU usage is back to normal, disabling challenge rule for {', '.join(domains)}...)")
                telegram_custom_message_end = input().strip()
                if not telegram_custom_message_end:
                    telegram_custom_message_end = f"The CPU usage is back to normal, disabling challenge rule for {', '.join(domains)}..."
                print("If you want to use a custom message for when the CPU usage is too high 10 seconds after the attack started, please enter the message (default: The CPU usage is still too high, the challenge rule might not be working...)")

                telegram_custom_message_10_seconds = input().strip()
                if not telegram_custom_message_10_seconds:
                    telegram_custom_message_10_seconds = f"The CPU usage is still too high, the challenge rule might not be working..."

    logging.debug(f"Telegram bot token: {telegram_bot_token}")
    logging.debug(f"Telegram chat ID: {telegram_chat_id}")
    logging.debug(f"Telegram custom message: {telegram_custom_message}")
    logging.debug(f"Telegram custom message end: {telegram_custom_message_end}")
    logging.debug(f"Telegram custom message 10 seconds: {telegram_custom_message_10_seconds}")
    

    print("How many seconds do you want to wait before disabling the challenge rule? (default: auto eg. 30)")
    disable_delay = input().strip()
    if not disable_delay:
        disable_delay = "auto"
    elif not re.match(r"^[0-9]+$", disable_delay):
        logging.error("Invalid disable delay, please enter a valid disable delay")
        return
    elif disable_delay < 0:
        logging.error("Disable delay cannot be less than 0")
        return
    elif disable_delay < 5:
        logging.warning("You have set the disable delay to a very low value, if you know what you are doing, you can ignore this message")
    elif disable_delay > 1800:
        logging.warning("You have set the disable delay to a very high value, if you know what you are doing, you can ignore this message")
    logging.debug(f"Disable delay: {disable_delay}")

    
    print("Do you want to use averaged CPU monitoring? (default: yes)")
    averaged_cpu_monitoring = input().strip().lower()
    if not averaged_cpu_monitoring:
        averaged_cpu_monitoring = True
    elif averaged_cpu_monitoring in ["true", "yes", "y"]:
        averaged_cpu_monitoring = True
    elif averaged_cpu_monitoring in ["false", "no", "n"]:
        averaged_cpu_monitoring = False
    else:
        logging.error("Invalid averaged CPU monitoring, setting to default (yes)")
        averaged_cpu_monitoring = True
    logging.debug(f"Averaged CPU monitoring: {averaged_cpu_monitoring}")


    print("Please enter the range of the averaged CPU monitoring (default: 10)")
    averaged_cpu_monitoring_range = input().strip()
    if not averaged_cpu_monitoring_range:
        averaged_cpu_monitoring_range = 10
    elif not re.match(r"^[0-9]+$", averaged_cpu_monitoring_range):
        logging.error("Invalid averaged CPU monitoring range, please enter a valid averaged CPU monitoring range")
        return
    elif int(averaged_cpu_monitoring_range) < 2:
        logging.error("Averaged CPU monitoring range cannot be less than 2")
        return
    elif int(averaged_cpu_monitoring_range) > 120:
        logging.warning("Averaged CPU monitoring range is too high, you can ignore this message if you know what you are doing")
    logging.debug(f"Averaged CPU monitoring range: {averaged_cpu_monitoring_range}")

    
    cf = Cloudflare(api_token=api_token)
    
    try:
        rulesets_page = cf.rulesets.list(zone_id=zone_id)
        logging.debug(f"Rulesets: {rulesets_page}")
        
        target_ruleset_id = None
        for ruleset in rulesets_page.result:
            if ruleset.phase == "http_request_firewall_custom":
                target_ruleset_id = ruleset.id
                break
        logging.debug(f"Target ruleset ID: {target_ruleset_id}")
        
        if not target_ruleset_id:
            logging.info("No http_request_firewall_custom ruleset found.")
            
            custom_ruleset = cf.rulesets.create(
                kind="zone",
                name="cf-shield-challenge",
                phase="http_request_firewall_custom",
                zone_id=zone_id
            )
            target_ruleset_id = custom_ruleset.id
        logging.debug(f"Target ruleset ID: {target_ruleset_id}")
        
        existing_ruleset = cf.rulesets.get(zone_id=zone_id, ruleset_id=target_ruleset_id)
        logging.debug(f"Existing ruleset: {existing_ruleset}")
        
        cf_shield_rule_id = None
        try:
            for rule in existing_ruleset.rules:
                if rule.description and "CF-Shield" in rule.description:
                    cf_shield_rule_id = rule.id
                    break
        except Exception as e:
            logging.error(f"Error checking for existing CF-Shield rule: {e}")
            cf_shield_rule_id = None
        logging.debug(f"CF-Shield rule ID: {cf_shield_rule_id}")
        
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
        logging.debug(f"CF-Shield rule ID: {cf_shield_rule_id}")

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
            f.write(f"SLACK_WEBHOOK={slack_webhook}\n")
            f.write(f"SLACK_CUSTOM_MESSAGE={slack_custom_message}\n")
            f.write(f"SLACK_CUSTOM_MESSAGE_END={slack_custom_message_end}\n")
            f.write(f"SLACK_CUSTOM_MESSAGE_10_SECONDS={slack_custom_message_10_seconds}\n")
            f.write(f"DISCORD_WEBHOOK={discord_webhook}\n")
            f.write(f"DISCORD_CUSTOM_MESSAGE={discord_custom_message}\n")
            f.write(f"DISCORD_CUSTOM_MESSAGE_END={discord_custom_message_end}\n")
            f.write(f"DISCORD_CUSTOM_MESSAGE_10_SECONDS={discord_custom_message_10_seconds}\n")
            f.write(f"TELEGRAM_BOT_TOKEN={telegram_bot_token}\n")
            f.write(f"TELEGRAM_CHAT_ID={telegram_chat_id}\n")
            f.write(f"TELEGRAM_CUSTOM_MESSAGE={telegram_custom_message}\n")
            f.write(f"TELEGRAM_CUSTOM_MESSAGE_END={telegram_custom_message_end}\n")
            f.write(f"TELEGRAM_CUSTOM_MESSAGE_10_SECONDS={telegram_custom_message_10_seconds}\n")
            f.write(f"DISABLE_DELAY={disable_delay}\n")
            f.write(f"AVERAGED_CPU_MONITORING={averaged_cpu_monitoring}\n")
            f.write(f"AVERAGED_CPU_MONITORING_RANGE={averaged_cpu_monitoring_range}\n")
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
    cpu_threshold = int(os.getenv("CPU_THRESHOLD", 80))
    challenge_type = os.getenv("CHALLENGE_TYPE", "managed_challenge")
    slack_webhook = os.getenv("SLACK_WEBHOOK", None)
    slack_custom_message = os.getenv("SLACK_CUSTOM_MESSAGE", None)
    slack_custom_message_end = os.getenv("SLACK_CUSTOM_MESSAGE_END", None)
    slack_custom_message_10_seconds = os.getenv("SLACK_CUSTOM_MESSAGE_10_SECONDS", None)
    discord_webhook = os.getenv("DISCORD_WEBHOOK", None)
    discord_custom_message = os.getenv("DISCORD_CUSTOM_MESSAGE", None)
    discord_custom_message_end = os.getenv("DISCORD_CUSTOM_MESSAGE_END", None)
    discord_custom_message_10_seconds = os.getenv("DISCORD_CUSTOM_MESSAGE_10_SECONDS", None)
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", None)
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", None)
    telegram_custom_message = os.getenv("TELEGRAM_CUSTOM_MESSAGE", None)
    telegram_custom_message_end = os.getenv("TELEGRAM_CUSTOM_MESSAGE_END", None)
    telegram_custom_message_10_seconds = os.getenv("TELEGRAM_CUSTOM_MESSAGE_10_SECONDS", None)
    disable_delay = os.getenv("DISABLE_DELAY", "auto")
    averaged_cpu_monitoring = os.getenv("AVERAGED_CPU_MONITORING", True)
    averaged_cpu_monitoring_range = os.getenv("AVERAGED_CPU_MONITORING_RANGE", 10)
    
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
    if disable_delay == "auto":
        new_disable_delay = 30
    else:
        new_disable_delay = disable_delay
    last_10_seconds = []
    attack_time = 0
    while True:
        time.sleep(1)
        try:
            if averaged_cpu_monitoring:
                current_cpu_usage = psutil.cpu_percent()
                logging.debug(f"Current CPU usage: {current_cpu_usage}%")
                last_10_seconds.append(current_cpu_usage)
                if len(last_10_seconds) > int(averaged_cpu_monitoring_range):
                    last_10_seconds.pop(0)
                cpu_usage = sum(last_10_seconds) / len(last_10_seconds)
                logging.debug(f"Averaged CPU usage: {cpu_usage}%")
            else:
                cpu_usage = psutil.cpu_percent()
                logging.debug(f"Current CPU usage: {cpu_usage}%")

            if cpu_usage > int(cpu_threshold):
                t = 0
                logging.debug(f"CPU usage ({cpu_usage}%) exceeds threshold ({cpu_threshold}%), t = 0")
            else:
                t += 1
                logging.debug(f"CPU usage ({cpu_usage}%) is below threshold ({cpu_threshold}%), t = {t} (t+1)")

            if t > (int(new_disable_delay) * 2) and (disable_delay == "auto"):
                new_disable_delay = 30
                logging.debug(f"New disable delay: {new_disable_delay}")
            
            if t == 0 and rule_enabled:
                attack_time += 1
                logging.debug(f"Attack time: {attack_time}")

            if attack_time > 10:
                if discord_webhook:
                    webhook = DiscordWebhook(url=discord_webhook, content=discord_custom_message_10_seconds)
                    webhook.execute()
                    logging.debug(f"Discord webhook executed (10 seconds after attack started)")
                if slack_webhook:
                    webhook = WebhookClient(slack_webhook)
                    webhook.send(text=slack_custom_message_10_seconds)
                    logging.debug(f"Slack webhook executed (10 seconds after attack started)")
                if telegram_bot_token:
                    send_telegram_message(telegram_custom_message_10_seconds, telegram_chat_id, telegram_bot_token)
                    logging.debug(f"Telegram webhook executed (10 seconds after attack started)")
                attack_time = 0
                logging.debug(f"Attack time reset to 0")

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

                if disable_delay == "auto":
                    logging.debug(f"Disable delay is auto, multiplying by 1.5 (new disable delay rn: {new_disable_delay})")
                    new_disable_delay = int(new_disable_delay) * 1.5
                    logging.debug(f"New disable delay: {new_disable_delay}")

                if discord_webhook:
                    webhook = DiscordWebhook(url=discord_webhook, content=discord_custom_message)
                    webhook.execute()
                    logging.debug(f"Discord webhook executed (attack started)")

                if slack_webhook:
                    webhook = WebhookClient(slack_webhook)
                    webhook.send(text=slack_custom_message)
                    logging.debug(f"Slack webhook executed (attack started)")

                if telegram_bot_token:
                    send_telegram_message(telegram_custom_message, telegram_chat_id, telegram_bot_token)
                    logging.debug(f"Telegram webhook executed (attack started)")
                
            elif t > int(new_disable_delay) and rule_enabled:
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
                    webhook = DiscordWebhook(url=discord_webhook, content=discord_custom_message_end)
                    webhook.execute()
                    logging.debug(f"Discord webhook executed (attack ended)")
                if slack_webhook:
                    webhook = WebhookClient(slack_webhook)
                    webhook.send(text=slack_custom_message_end)
                    logging.debug(f"Slack webhook executed (attack ended)")
                if telegram_bot_token:
                    send_telegram_message(telegram_custom_message_end, telegram_chat_id, telegram_bot_token)
                    logging.debug(f"Telegram webhook executed (attack ended)")
                
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
    logger = logging.getLogger()
    if os.getenv("DEBUG") == "true":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    if os.getenv("DEBUG") == "true":
        console_handler.setLevel(logging.DEBUG)
    else:
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

    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
    else:
        run()