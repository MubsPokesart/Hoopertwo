"""Diagnostic script to verify bot configuration and generate correct invite URL."""
import discord
from src.config.settings import Settings


def main():
    """Print bot information and generate correct invite URL."""
    settings = Settings()

    print("=" * 50)
    print("BOT VERIFICATION DIAGNOSTICS")
    print("=" * 50)

    # Print token info (first/last 6 chars only for security)
    token = settings.discord_token
    print(f"\nToken (partial): {token[:6]}...{token[-6:]}")
    print(f"Token length: {len(token)} chars")

    # Parse bot user ID from token
    # Discord tokens format: <user_id_base64>.<timestamp>.<hmac>
    try:
        import base64
        user_id_base64 = token.split('.')[0]
        # Add padding if needed
        padding = 4 - (len(user_id_base64) % 4)
        if padding != 4:
            user_id_base64 += '=' * padding
        user_id = base64.b64decode(user_id_base64).decode('utf-8')
        print(f"\nBot User ID (from token): {user_id}")
    except Exception as e:
        print(f"\nCouldn't parse user ID from token: {e}")
        user_id = "UNKNOWN"

    print("\n" + "=" * 50)
    print("VERIFICATION STEPS:")
    print("=" * 50)

    print("\n1. Go to Discord Developer Portal:")
    print("   https://discord.com/developers/applications")

    print("\n2. Click on 'HooperTwo' application")

    print("\n3. Check APPLICATION ID (left sidebar, under app name)")
    print(f"   Should match: {user_id}")

    print("\n4. Verify Privileged Gateway Intents (Bot tab):")
    print("   ✓ PRESENCE INTENT (optional)")
    print("   ✓ SERVER MEMBERS INTENT (REQUIRED)")
    print("   ✓ MESSAGE CONTENT INTENT (REQUIRED)")

    if user_id != "UNKNOWN":
        print("\n5. Use this CORRECT invite URL:")
        print("\n" + "=" * 50)
        invite_url = (
            f"https://discord.com/api/oauth2/authorize"
            f"?client_id={user_id}"
            f"&permissions=8"  # Administrator
            f"&scope=bot%20applications.commands"
        )
        print(invite_url)
        print("=" * 50)
        print("\n   Copy this URL and paste in browser")
        print("   Select your test server")
        print("   Click 'Authorize'")

    print("\n6. After authorizing, run the bot:")
    print("   poetry run python bot.py")
    print("\n   You should see 'Connected to 1 guilds' (or more)")

    print("\n" + "=" * 50)
    print("If the bot STILL shows 0 guilds:")
    print("- The invite URL used a DIFFERENT application's Client ID")
    print("- Check if you have multiple bot applications")
    print("- Verify you're looking at the correct application in Portal")
    print("=" * 50)


if __name__ == "__main__":
    main()
