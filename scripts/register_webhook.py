"""
One-time script to register the Strava webhook subscription.

Usage:
    uv run register_webhook.py --callback-url https://<your-public-host>/webhook

Run ONCE after the webhook service is publicly reachable (e.g. via ngrok or a VPS).
Strava will immediately do a GET validation call to the callback URL, so the
webhook service must already be running when you execute this script.
"""

import argparse
import os

import requests
from dotenv import load_dotenv

load_dotenv()

PUSH_SUBSCRIPTIONS_URL = "https://www.strava.com/api/v3/push_subscriptions"


def register(callback_url: str) -> None:
    resp = requests.post(
        PUSH_SUBSCRIPTIONS_URL,
        data={
            "client_id": os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "callback_url": callback_url,
            "verify_token": os.environ["STRAVA_VERIFY_TOKEN"],
        },
        timeout=15,
    )

    if resp.status_code == 201:
        data = resp.json()
        print(f"Webhook subscription registered successfully.")
        print(f"  Subscription ID : {data['id']}")
        print(f"  Callback URL    : {callback_url}")
    else:
        print(f"Failed to register webhook: {resp.status_code}")
        print(resp.text)


def list_subscriptions() -> None:
    resp = requests.get(
        PUSH_SUBSCRIPTIONS_URL,
        params={
            "client_id": os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    subs = resp.json()
    if not subs:
        print("No active webhook subscriptions.")
    for s in subs:
        print(f"  id={s['id']}  callback_url={s['callback_url']}")


def delete_subscription(subscription_id: int) -> None:
    resp = requests.delete(
        f"{PUSH_SUBSCRIPTIONS_URL}/{subscription_id}",
        data={
            "client_id": os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
        },
        timeout=15,
    )
    if resp.status_code == 204:
        print(f"Subscription {subscription_id} deleted.")
    else:
        print(f"Failed: {resp.status_code} – {resp.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Strava webhook subscriptions")
    sub = parser.add_subparsers(dest="command", required=True)

    reg = sub.add_parser("register", help="Register a new webhook subscription")
    reg.add_argument("--callback-url", required=True, help="Public URL of the /webhook endpoint")

    sub.add_parser("list", help="List active subscriptions")

    rm = sub.add_parser("delete", help="Delete a subscription")
    rm.add_argument("--id", type=int, required=True, help="Subscription ID to delete")

    args = parser.parse_args()

    if args.command == "register":
        register(args.callback_url)
    elif args.command == "list":
        list_subscriptions()
    elif args.command == "delete":
        delete_subscription(args.id)
