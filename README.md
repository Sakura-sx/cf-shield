# CF-Shield

CF-Shield is a Python script for detecting DDoS attacks and enabling security measures on Cloudflare automatically.

## Installation

First, you will need to get your Cloudflare email, API token, zone ID, and account ID.

```bash
git clone https://github.com/Sakura-sx/cf-shield.git
cd cf-shield
python3 main.py
```
When running the script for the first time, it will ask you for your Cloudflare email, API token, zone ID, and account ID.

The dependencies should be installed automatically. If not, you can install them manually by running `python3 -m pip install -r requirements.txt`.


## Usage

```bash
python3 main.py
```
To modify the config, you can edit the .env file.

## Roadmap
- [x] Adding a way to add multiple domains.
- [x] Making the challenge type customizable instead of `managed_challenge`.
- [x] Discord webhook notifications.
- [x] Adding a configurable delay before disabling the challenge rule.
- [x] Telegram notifications.
- [ ] Slack notifications.
- [ ] Add ratelimit challenge.


## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[GPL-3.0](https://choosealicense.com/licenses/gpl-3.0/)