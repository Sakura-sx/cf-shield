import os
import re
import sys
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
    from slack_sdk.webhook import WebhookClient
except ImportError:
    print("installing dependencies...")
    os.system("python3 -m pip install -r requirements.txt")

def setup_domains():
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
    return domains

def setup_email():
    print("What's the email you used to sign up for Cloudflare? (e.g. example@example.com)")
    email = input().strip()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        logging.error(f"Invalid email: {email}")
        return
    logging.debug(f"Email: {email}")
    return email

def setup_api_token():
    print("Please create an API token and copy it here (e.g. aK-MaF3oyTrPDD8YoNBlvqo0ous7BOeSA7te84OR)")
    api_token = input().strip()
    if not re.match(r"^[a-zA-Z0-9-]{40}$", api_token):
        logging.error(f"Invalid API token: {api_token}")
        return
    logging.debug(f"API token: {api_token}")
    return api_token

def setup_zone_id():
    print("Please copy the zone ID from the URL of your Cloudflare dashboard (e.g. 1b7c0e3d41f09ceb9cbcde6b0c7bc819)")
    zone_id = input().strip()
    if not re.match(r"^[a-zA-Z0-9]{32}$", zone_id):
        logging.error(f"Invalid zone ID: {zone_id}")
        return
    logging.debug(f"Zone ID: {zone_id}")
    return zone_id

def setup_account_id(zone_id):
    print("Please copy the account ID from the URL of your Cloudflare dashboard (e.g. 6dead821d9eb4c42f8a8dda399651660)")
    account_id = input().strip()
    if not re.match(r"^[a-zA-Z0-9]{32}$", account_id):
        logging.error(f"Invalid account ID: {account_id}")
        return
    elif zone_id == account_id:
        logging.error("Zone ID and account ID are the same, that means you pasted one of them in the wrong place")
        return
    logging.debug(f"Account ID: {account_id}")
    return account_id

def setup_cpu_threshold():
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
    logging.debug(f"CPU threshold: {cpu_threshold}")
    return int(cpu_threshold)

def setup_challenge_type():
    print("What's the challenge type you want to use? (default: managed_challenge, options: managed_challenge, js_challenge, challenge)")
    challenge_type = input().strip()
    if not challenge_type:
        challenge_type = "managed_challenge"
    elif challenge_type not in ["managed_challenge", "js_challenge", "challenge"]:
        logging.error("Invalid challenge type, please enter a valid challenge type")
        return
    logging.debug(f"Challenge type: {challenge_type}")
    return challenge_type

def setup_slack_webhook(domains):
    print("If you want to use a Slack webhook, please enter the webhook URL (default: None)")
    slack_webhook = input().strip()
    if not slack_webhook:
        return None, None, None, None
    else:
        if not re.match(r"^https:\/\/hooks\.slack\.com\/services\/[A-Za-z0-9\/]+$", slack_webhook):
            logging.error("Invalid Slack webhook URL, please enter a valid Slack webhook URL")
            return "error"
        else:
            logging.info("Sending a test message to the Slack webhook...")
            try:
                webhook = WebhookClient(slack_webhook)
                webhook.send(text="Test message from CF-Shield")
                logging.info("Test message sent successfully!")
            except Exception as e:
                logging.error(f"Error sending test message to Slack webhook: {e}")
                return "error"
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
                return slack_webhook, slack_custom_message, slack_custom_message_end, slack_custom_message_10_seconds

def setup_discord_webhook(domains):
    print("If you want to use a Discord webhook, please enter the webhook URL (default: None)")
    discord_webhook = input().strip()
    if not discord_webhook:
        return None, None, None, None
    else:
        if not re.match(r"^https:\/\/(discord\.com|ptb\.discord\.com|canary\.discord\.com)\/api\/webhooks\/[0-9]+\/[a-zA-Z0-9-]+$", discord_webhook):
            logging.error("Invalid Discord webhook URL, please enter a valid Discord webhook URL")
            return "error"
        else:
            logging.info("Sending a test message to the Discord webhook...")
            try:
                webhook = DiscordWebhook(url=discord_webhook, content="Test message from CF-Shield")
                webhook.execute()
                logging.info("Test message sent successfully!")
            except Exception as e:
                logging.error(f"Error sending test message to Discord webhook: {e}")
                return "error"
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
                return discord_webhook, discord_custom_message, discord_custom_message_end, discord_custom_message_10_seconds

def setup_telegram_bot(domains):
    print("If you want to use a Telegram bot, please enter the bot token (default: None)")
    telegram_bot_token = input().strip()
    if not telegram_bot_token:
        return None, None, None, None, None
    else:
        if not re.match(r"([0-9]{8,10}):[A-za-z0-9]{35}", telegram_bot_token):
            logging.error("Invalid Telegram bot token, please enter a valid Telegram bot token")
            return "error"
        print("Please enter the chat ID for the telegram bot")
        telegram_chat_id = input().strip()
        if not re.match(r"^[0-9]+$", telegram_chat_id):
            logging.error("Invalid Telegram chat ID, please enter a valid Telegram chat ID")
            return "error"
        else:
            logging.info("Sending a test message to the Telegram bot...")
            try:
                send_telegram_message("Test message from CF-Shield", telegram_chat_id, telegram_bot_token)
                logging.info("Test message sent successfully!")
            except Exception as e:
                logging.error(f"Error sending test message to Telegram bot: {e}")
                return "error"
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
                return telegram_bot_token, telegram_chat_id, telegram_custom_message, telegram_custom_message_end, telegram_custom_message_10_seconds

def setup_disable_delay():
    print("How many seconds do you want to wait before disabling the challenge rule? (default: auto eg. 30)")
    disable_delay = input().strip()
    if not disable_delay:
        return "auto"
    elif disable_delay == "auto":
        return "auto"
    elif not re.match(r"^[0-9]+$", disable_delay):
        logging.error("Invalid disable delay, please enter a valid disable delay")
        return None
    elif int(disable_delay) < 0:
        logging.error("Disable delay cannot be less than 0")
        return None
    elif int(disable_delay) < 5:
        logging.error("You have set the disable delay to a very low value, if you know what you are doing, you can ignore this message")
    elif int(disable_delay) > 1800:
        logging.error("You have set the disable delay to a very high value, if you know what you are doing, you can ignore this message")
    logging.debug(f"Disable delay: {disable_delay}")
    return int(disable_delay)

def setup_averaged_cpu_monitoring():
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
    return averaged_cpu_monitoring

def setup_averaged_cpu_monitoring_range():
    print("Please enter the range of the averaged CPU monitoring (default: 10)")
    averaged_cpu_monitoring_range = input().strip()
    if not averaged_cpu_monitoring_range:
        averaged_cpu_monitoring_range = 10
    elif not re.match(r"^[0-9]+$", averaged_cpu_monitoring_range):
        logging.error("Invalid averaged CPU monitoring range, setting to default (10)")
        averaged_cpu_monitoring_range = 10
    elif int(averaged_cpu_monitoring_range) < 2:
        logging.error("Averaged CPU monitoring range cannot be less than 2")
        return None
    elif int(averaged_cpu_monitoring_range) > 120:
        logging.warning("Averaged CPU monitoring range is too high, you can ignore this message if you know what you are doing")
    logging.debug(f"Averaged CPU monitoring range: {averaged_cpu_monitoring_range}")
    return int(averaged_cpu_monitoring_range)


def setup_enable_bandwidth_monitoring():
    print("Do you want to use bandwidth monitoring? (default: no)")
    enable_bandwidth_monitoring = input().strip().lower()
    if not enable_bandwidth_monitoring:
        enable_bandwidth_monitoring = False
    elif enable_bandwidth_monitoring in ["true", "yes", "y"]:
        enable_bandwidth_monitoring = True
    elif enable_bandwidth_monitoring in ["false", "no", "n"]:
        enable_bandwidth_monitoring = False
    else:
        logging.error("Invalid enable bandwidth monitoring, setting to default (no)")
        enable_bandwidth_monitoring = False
    logging.debug(f"Enable bandwidth monitoring: {enable_bandwidth_monitoring}")
    if enable_bandwidth_monitoring:
        print("Please enter the ingoing limit with the unit, no unit means bits per second (default: 50000000, 50Mbps)")
        ingoing_limit = input().strip()
        ingoing_limit = setup_ingoing_limit(ingoing_limit)
        print("Please enter the outgoing limit with the unit, no unit means bits per second (default: 50000000, 50Mbps)")
        outgoing_limit = input().strip()
        outgoing_limit = setup_outgoing_limit(outgoing_limit)
        return True,ingoing_limit, outgoing_limit
    else:
        return False, None, None

def setup_ingoing_limit(ingoing_limit):
    multiplier = 1
    new_ingoing_limit = ""
    if not ingoing_limit:
        return int(50000000) #50Mbps
    else:
        for char in ingoing_limit:
            if char.isdigit():
                new_ingoing_limit += str(char)
            elif char == "B":
                multiplier = multiplier * 8
            elif char == "b":
                continue
            elif char.lower() == "k":
                multiplier = multiplier * 1000
            elif char.lower() == "m":
                multiplier = multiplier * 1000000
            elif char.lower() == "g":
                multiplier = multiplier * 1000000000
            elif char == "/":
                continue
            elif char.lower() == "s":
                continue
            elif char.lower() == "p":
                continue
            else:
                logging.error("Invalid ingoing limit, setting to default (50Mbps)")
                return int(50000000)

        ingoing_limit = int(new_ingoing_limit) * multiplier
    logging.debug(f"Ingoing limit: {ingoing_limit}bps")
    return int(ingoing_limit)

def setup_outgoing_limit(outgoing_limit):
    multiplier = 1
    new_outgoing_limit = ""
    if not outgoing_limit:
        return int(50000000) #50Mbps
    else:
        for char in outgoing_limit:
            if char.isdigit():
                new_outgoing_limit += str(char)
            elif char == "B":
                multiplier = multiplier * 8
            elif char == "b":
                continue
            elif char.lower() == "k":
                multiplier = multiplier * 1000
            elif char.lower() == "m":
                multiplier = multiplier * 1000000
            elif char.lower() == "g":
                multiplier = multiplier * 1000000000
            elif char == "/":
                continue
            elif char.lower() == "s":
                continue
            elif char.lower() == "p":
                continue
            else:
                logging.error("Invalid outgoing limit, setting to default (50Mbps)")
                return int(50000000)

        outgoing_limit = int(new_outgoing_limit) * multiplier
    logging.debug(f"Outgoing limit: {outgoing_limit}bps")
    return int(outgoing_limit)

def setup():
    while True:
        try:
            domains = setup_domains()
            if domains is not None:
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up domains: {e}, please try again")
            continue

    while True:
        try:
            email = setup_email()
            if email is not None:
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up email: {e}, please try again")
            continue

    while True:
        try:
            api_token = setup_api_token()
            if api_token is not None:
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up API token: {e}, please try again")
            continue

    while True:
        try:
            zone_id = setup_zone_id()
            if zone_id is None:
                logging.error("Please try again")
                continue
        except Exception as e:
            logging.error(f"Error setting up zone ID: {e}, please try again")
            continue
        try:
            account_id = setup_account_id(zone_id)
            if account_id is None:
                logging.error("Please try again, you will be sent back to setting up the zone ID in case you made a mistake")
                continue
        except Exception as e:
            logging.error(f"Error setting up account ID: {e}, please try again")
            continue

        break
    while True:
        try:
            cpu_threshold = setup_cpu_threshold()
            if cpu_threshold is not None:
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up CPU threshold: {e}, please try again")
            continue
    
    while True:
        try:
            challenge_type = setup_challenge_type()
            if challenge_type is not None:
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up challenge type: {e}, please try again")
            continue
    
    while True:
        try:
            slack_webhook, slack_custom_message, slack_custom_message_end, slack_custom_message_10_seconds = setup_slack_webhook(domains)
            if slack_webhook != "error":
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up Slack webhook: {e}, please try again")
            continue
    
    while True:
        try:
            discord_webhook, discord_custom_message, discord_custom_message_end, discord_custom_message_10_seconds = setup_discord_webhook(domains)
            if discord_webhook != "error":
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up Discord webhook: {e}, please try again")
            continue
    
    while True:
        try:
            telegram_bot_token, telegram_chat_id, telegram_custom_message, telegram_custom_message_end, telegram_custom_message_10_seconds = setup_telegram_bot(domains)
            if telegram_bot_token != "error":
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up Telegram bot: {e}, please try again")
            continue
    
    while True:
        try:
            disable_delay = setup_disable_delay()
            if disable_delay is not None:
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up disable delay: {e}, please try again")
            continue
    
    while True:
        try:
            averaged_cpu_monitoring = setup_averaged_cpu_monitoring()
            if averaged_cpu_monitoring is not None:
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up averaged CPU monitoring: {e}, please try again")
            continue
    
    while True:
        try:
            averaged_cpu_monitoring_range = setup_averaged_cpu_monitoring_range()
            if averaged_cpu_monitoring_range is not None:
                break
            logging.error("Please try again")
        except Exception as e:
            logging.error(f"Error setting up averaged CPU monitoring range: {e}, please try again")
            continue

    while True:
        try:
            enable_bandwidth_monitoring, ingoing_limit, outgoing_limit = setup_enable_bandwidth_monitoring()
            if enable_bandwidth_monitoring:
                if ingoing_limit is None or outgoing_limit is None:
                    logging.error("Please try again")
                    continue
                else:
                    break
            else:
                break
        except Exception as e:
            logging.error(f"Error setting up bandwidth monitoring: {e}, please try again")
            continue

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
        return None

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
            f.write(f"TRAFFIC_MONITORING={enable_bandwidth_monitoring}\n")
            f.write(f"INGOING_LIMIT={ingoing_limit}\n")
            f.write(f"OUTGOING_LIMIT={outgoing_limit}\n")
            f.write(f"SETUP=true\n")
        print("Configuration saved successfully!")
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        return None
        
    print("Setup complete! Starting monitoring...")
    main()

def send_telegram_message(message, chat_id, bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(url, json=data)

def notify(message, slack_webhook=None, discord_webhook=None, telegram_bot_token=None, chat_id=None):
    if slack_webhook:
        webhook = WebhookClient(slack_webhook)
        webhook.send(text=message)
        logging.debug(f"Slack webhook executed (notify)")
    if discord_webhook:
        webhook = DiscordWebhook(url=discord_webhook, content=message)
        webhook.execute()
        logging.debug(f"Discord webhook executed (notify)")
    if telegram_bot_token:
        send_telegram_message(message, chat_id, telegram_bot_token)
        logging.debug(f"Telegram webhook executed (notify)")

def get_cpu_usage(averaged_cpu_monitoring, last_readings, averaged_cpu_monitoring_range):
    current_cpu_usage = psutil.cpu_percent()
    
    if averaged_cpu_monitoring:
        logging.debug(f"Current CPU usage: {current_cpu_usage}%")
        last_readings.append(current_cpu_usage)
        if len(last_readings) > int(averaged_cpu_monitoring_range):
            last_readings.pop(0)
        cpu_usage = sum(last_readings) / len(last_readings)
        logging.debug(f"Averaged CPU usage: {cpu_usage}%")
        return cpu_usage
    else:
        logging.debug(f"Current CPU usage: {current_cpu_usage}%")
        return current_cpu_usage

def get_bandwidth_usage():
    stats = psutil.net_io_counters()
    current_ingoing_traffic = stats.bytes_recv
    current_outgoing_traffic = stats.bytes_sent
    
    logging.debug(f"Current ingoing traffic: {current_ingoing_traffic} bytes")
    logging.debug(f"Current outgoing traffic: {current_outgoing_traffic} bytes")
    
    return current_ingoing_traffic, current_outgoing_traffic

def check_thresholds(cpu_usage, cpu_threshold, current_ingoing_traffic=None, 
                    ingoing_limit=None, current_outgoing_traffic=None, outgoing_limit=None):
    attack_detected = False
    
    # CPU
    if cpu_usage > int(cpu_threshold):
        logging.debug(f"CPU usage ({cpu_usage}%) exceeds threshold ({cpu_threshold}%)")
        attack_detected = True
    else:
        logging.debug(f"CPU usage ({cpu_usage}%) is below threshold ({cpu_threshold}%)")
    
    # Bandwidth
    if current_ingoing_traffic is not None and ingoing_limit is not None:
        if current_ingoing_traffic > ingoing_limit:
            logging.debug(f"Ingoing traffic ({current_ingoing_traffic} bytes) exceeds limit ({ingoing_limit} bytes)")
            attack_detected = True
        else:
            logging.debug(f"Ingoing traffic ({current_ingoing_traffic} bytes) is below limit ({ingoing_limit} bytes)")
    
    if current_outgoing_traffic is not None and outgoing_limit is not None:
        if current_outgoing_traffic > outgoing_limit:
            logging.debug(f"Outgoing traffic ({current_outgoing_traffic} bytes) exceeds limit ({outgoing_limit} bytes)")
            attack_detected = True
        else:
            logging.debug(f"Outgoing traffic ({current_outgoing_traffic} bytes) is below limit ({outgoing_limit} bytes)")
    
    return attack_detected

def manage_cloudflare_rule(cf, rule_enabled, attack_detected, timer, disable_delay, 
                          rule_id, ruleset_id, zone_id, cpu_usage, cpu_threshold,
                          discord_custom_message, discord_webhook, slack_custom_message, 
                          slack_webhook, telegram_custom_message, telegram_bot_token, 
                          telegram_chat_id, discord_custom_message_end, 
                          slack_custom_message_end, telegram_custom_message_end):
    new_rule_enabled = rule_enabled
    
    if attack_detected and not rule_enabled:
        logging.info(f"CPU usage ({cpu_usage}%) exceeds threshold ({cpu_threshold}%)")
        cf.rulesets.rules.edit(
            rule_id=rule_id,
            ruleset_id=ruleset_id,
            zone_id=zone_id,
            enabled=True
        )
        new_rule_enabled = True
        logging.info("Challenge rule enabled!")
        
        notify(discord_custom_message, discord_webhook)
        notify(slack_custom_message, slack_webhook)
        notify(telegram_custom_message, telegram_bot_token, telegram_chat_id)
        
    elif timer > int(disable_delay) and rule_enabled:
        logging.info("CPU usage returned to normal, disabling challenge rule...")
        cf.rulesets.rules.edit(
            rule_id=rule_id,
            ruleset_id=ruleset_id,
            zone_id=zone_id,
            enabled=False
        )
        new_rule_enabled = False
        logging.info("Challenge rule disabled!")
        
        notify(discord_custom_message_end, discord_webhook)
        notify(slack_custom_message_end, slack_webhook)
        notify(telegram_custom_message_end, telegram_bot_token, telegram_chat_id)
    
    return new_rule_enabled

def update_timer_and_delay(attack_detected, timer, disable_delay, new_disable_delay):
    if attack_detected:
        new_timer = 0
        logging.debug(f"Attack detected, timer reset to 0")
        
        if disable_delay == "auto":
            updated_disable_delay = int(new_disable_delay) * 1.5
            logging.debug(f"Disable delay is auto, multiplying by 1.5 (new disable delay: {updated_disable_delay})")
            return new_timer, updated_disable_delay
    else:
        new_timer = timer + 1
        logging.debug(f"No attack detected, timer = {new_timer}")
        
        if new_timer > (int(new_disable_delay) * 2) and (disable_delay == "auto"):
            updated_disable_delay = 30
            logging.debug(f"Timer exceeded double delay, reset disable delay to: {updated_disable_delay}")
            return new_timer, updated_disable_delay
    
    return new_timer, new_disable_delay

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
    enable_bandwidth_monitoring = os.getenv("TRAFFIC_MONITORING", False)
    ingoing_limit = int(os.getenv("INGOING_LIMIT", 50000000)) #50Mbps
    outgoing_limit = int(os.getenv("OUTGOING_LIMIT", 50000000)) #50Mbps
    
    if not all([zone_id, ruleset_id, rule_id]):
        logging.error("Missing configuration. Please run setup again.")
        logging.error(f"Zone ID: {zone_id}")
        logging.error(f"Ruleset ID: {ruleset_id}")
        logging.error(f"Rule ID: {rule_id}")
        return None
    
    logging.info(f"Monitoring CPU usage for domains: {', '.join(domains)}")
    logging.info(f"CPU threshold: {cpu_threshold}%")
    
    # Initialize monitoring variables
    rule_enabled = False
    timer = 1
    new_disable_delay = 30 if disable_delay == "auto" else disable_delay
    last_cpu_readings = []
    attack_time = 0
    
    while True:
        time.sleep(1)
        try:
            # Get CPU usage (averaged or direct)
            cpu_usage = get_cpu_usage(averaged_cpu_monitoring, last_cpu_readings, averaged_cpu_monitoring_range)
            
            # Get bandwidth usage if monitoring is enabled
            current_ingoing_traffic = None
            current_outgoing_traffic = None
            if enable_bandwidth_monitoring:
                current_ingoing_traffic, current_outgoing_traffic = get_bandwidth_usage()
            
            # Check all thresholds
            attack_detected = check_thresholds(
                cpu_usage, cpu_threshold,
                current_ingoing_traffic, ingoing_limit if enable_bandwidth_monitoring else None,
                current_outgoing_traffic, outgoing_limit if enable_bandwidth_monitoring else None
            )
            
            # Update timer and disable delay
            timer, new_disable_delay = update_timer_and_delay(attack_detected, timer, disable_delay, new_disable_delay)
            
            # Track attack time for 10-second notification
            if attack_detected and rule_enabled:
                attack_time += 1
                logging.debug(f"Attack time: {attack_time}")
                
                if attack_time > 10:
                    notify(discord_custom_message_10_seconds, discord_webhook)
                    notify(slack_custom_message_10_seconds, slack_webhook)
                    notify(telegram_custom_message_10_seconds, telegram_bot_token, telegram_chat_id)
                    attack_time = 0
                    logging.debug(f"Attack time reset to 0")
            
            # Manage Cloudflare rule
            rule_enabled = manage_cloudflare_rule(
                cf, rule_enabled, attack_detected, timer, new_disable_delay,
                rule_id, ruleset_id, zone_id, cpu_usage, cpu_threshold,
                discord_custom_message, discord_webhook, slack_custom_message, slack_webhook,
                telegram_custom_message, telegram_bot_token, telegram_chat_id,
                discord_custom_message_end, slack_custom_message_end, telegram_custom_message_end
            )
                
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