# Connecting GitHub to Canva and YouTube (one-time)

The **Sign in (Canva / YouTube)** workflow does a one-time sign-in. It saves a long-lived refresh token as a repository secret, which later workflows use to fill Canva templates and upload to YouTube. No passwords or tokens go into chat or the repo.

## Before you start (repository secrets)

Add these under Settings > Secrets and variables > Actions:

| Secret | Where it comes from |
|---|---|
| `GH_SECRETS_TOKEN` | GitHub > your profile > Settings > Developer settings > Personal access tokens > **Fine-grained tokens** > Generate. Repository access: only `quiz-automation`. Permissions: **Secrets: Read and write**. Lets the workflows save refresh tokens (Canva issues a new one each time it is used). |
| `CANVA_CLIENT_SECRET` (secret) and `CANVA_CLIENT_ID` (repository **variable**, so GitHub doesn't hide it as `***` in the sign-in link) | Canva Developer Portal > Quiz Automations > Outside Canva > Configuration. Redirect URL must include `http://127.0.0.1:3001/oauth/redirect`. |
| `YT_CLIENT_SECRET` (secret) and `YT_CLIENT_ID` (repository **variable**) | Google Cloud, see below. |

### YouTube: Google Cloud setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and pick a project. Reuse the rain channel's project if it already uploads with scheduled publishing, otherwise create "Quiz automation".
2. Go to APIs & Services > Library and enable **YouTube Data API v3**.
3. Set up the OAuth consent screen (Google Auth Platform):
   1. Choose External, enter the app name and your email.
   2. Under Audience, set the publishing status to **In production**. In "Testing", sign-ins expire every 7 days.
4. Go to Credentials > Create credentials > **OAuth client ID**, choose the application type **Desktop app**, and copy the client ID and secret into `YT_CLIENT_ID` and `YT_CLIENT_SECRET`.

When you sign in, Google may warn that the app isn't verified. That's normal for your own app: choose Advanced > Go to … (unsafe), then sign in **as the One More Quiz channel** (pick the brand account if asked).

## Running the sign-in (per service)

1. Go to Actions > **Sign in (Canva / YouTube)** > Run workflow. Pick `canva` or `youtube` and leave Redirect URL blank.
2. Open the finished run. The summary has a sign-in link. Open it and approve.
3. The browser lands on a page that won't load (`127.0.0.1…`). That's expected. Copy the **whole address** from the address bar.
4. Within about 5 minutes, run the workflow again with the same service, pasting that address into **Redirect URL**.
5. The run summary should say "sign-in complete" and name the secret it saved: `CANVA_REFRESH_TOKEN` or `YT_REFRESH_TOKEN`.

If step 4 fails with an expired code, start again at step 1.

## Notes

- The repo is public, so run pages are visible to anyone. The sign-in link and the pasted address are useless without the client secret, and the code in the address can be used only once. Tokens are masked in the logs.
- Re-run the sign-in if the channel or Canva account is changed, deleted or reinstated, or if access is removed. Giulia reinstated the One More Quiz channel on 4 Nov 2026, so any earlier YouTube sign-in should be treated as gone.
- **YouTube API audit:** uploads from a project that YouTube hasn't audited are locked to private, so scheduled publishing (`publishAt`) won't take effect. See PLAN.md, "Before building", step 1.
