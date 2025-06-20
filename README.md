# CF-Shield

CF-Shield is a Python script for detecting DDoS attacks and enabling security measures on Cloudflare automatically.

## Installation

First, you will need to get your Cloudflare email, API token, zone ID, and account ID.

```bash
git clone https://github.com/Sakura-sx/CF-Shield.git
cd CF-Shield
pip install -r requirements.txt
python main.py
```
When running the script for the first time, it will ask you for your Cloudflare email, API token, zone ID, and account ID.

## Usage

```bash
python main.py
```
To modify any config, you can edit the .env file.

## Roadmap
- [ ] Adding a way to add multiple domains.
- [ ] Making the challenge type customizable instead of `managed_challenge`.
- [ ] Discord webhook notifications.

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[GPL-3.0](https://choosealicense.com/licenses/gpl-3.0/)