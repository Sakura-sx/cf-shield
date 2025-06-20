import os
try:
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
    print("What's the domain you want to use? (e.g. example.com)")
    domain = input()
    print("What's the email you used to sign up for Cloudflare? (e.g. example@example.com)")
    email = input()
    print("Please create an API token and copy it here (e.g. 1234567890abcdef)")
    api_token = input()
    print("Please copy the zone ID from the URL of your Cloudflare dashboard (e.g. 1b7c0e3d41f09ceb9cbcde6b0c7bc819)")
    zone_id = input()
    print("Please copy the account ID from the URL of your Cloudflare dashboard (e.g. 6dead821d9eb4c42f8a8dda399651660)")
    account_id = input()
    print("Please enter the CPU usage threshold in percentage (default: 80)")
    cpu_threshold = input()
    print("What's the challenge type you want to use? (default: managed_challenge)")
    challenge_type = input()
    print("If you want to use a discord webhook, please enter the webhook URL (default: None)")
    discord_webhook = input()
    print("How many seconds do you want to wait before disabling the challenge rule? (default: 30)")
    disable_delay = int(input())

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
            new_rule = cf.rulesets.rules.create(
                ruleset_id=target_ruleset_id,
                zone_id=zone_id,
                action=challenge_type,
                expression=f"(http.host eq \"{domain}\")",
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
            f.write(f"DOMAIN={domain}\n")
            f.write(f"CPU_THRESHOLD={cpu_threshold}\n")
            f.write(f"CHALLENGE_TYPE={challenge_type}\n")
            f.write(f"DISCORD_WEBHOOK={discord_webhook}\n")
            f.write(f"DISABLE_DELAY={disable_delay}\n")
            f.write(f"SETUP=true\n")
        print("Configuration saved successfully!")
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        return
        
    print("Setup complete! Starting monitoring...")
    main()


def main():
    
    cf = Cloudflare(api_token=os.getenv("CF_API_TOKEN"))
    zone_id = os.getenv("CF_ZONE_ID")
    account_id = os.getenv("CF_ACCOUNT_ID")
    ruleset_id = os.getenv("CF_RULESET_ID")
    rule_id = os.getenv("CF_RULE_ID")
    domain = os.getenv("DOMAIN")
    cpu_threshold = float(os.getenv("CPU_THRESHOLD", "80"))
    challenge_type = os.getenv("CHALLENGE_TYPE", "managed_challenge")
    discord_webhook = os.getenv("DISCORD_WEBHOOK", None)
    disable_delay = int(os.getenv("DISABLE_DELAY", 30))
    
    if not all([zone_id, ruleset_id, rule_id]):
        logging.error("Missing configuration. Please run setup again.")
        logging.error(f"Zone ID: {zone_id}")
        logging.error(f"Ruleset ID: {ruleset_id}")
        logging.error(f"Rule ID: {rule_id}")
        return
    
    logging.info(f"Monitoring CPU usage for domain: {domain}")
    logging.info(f"CPU threshold: {cpu_threshold}%")
    
    rule_enabled = False
    
    while True:
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            logging.info(f"Current CPU usage: {cpu_usage}%")

            if cpu_usage > cpu_threshold:
                t = 0
            else:
                t += 1
                time.sleep(1)
            
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
                    webhook = DiscordWebhook(url=discord_webhook, content=f"The CPU usage is too high, enabling challenge rule for {domain}...")
                    webhook.execute()
                
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
                    webhook = DiscordWebhook(url=discord_webhook, content=f"The CPU usage is back to normal, disabling challenge rule for {domain}...")
                    webhook.execute()
                
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